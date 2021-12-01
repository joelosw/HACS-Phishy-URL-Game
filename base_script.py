"""Select labels from a QM annotation job.

"""

import argparse
import json
import os
import sys
import time
import urllib.request
from collections import defaultdict
from itertools import zip_longest
from queue import Empty, Queue
from threading import Thread
from typing import Dict, List, Optional, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageQt
from PyQt5 import QtCore
from PyQt5.QtGui import QIcon, QKeySequence, QPixmap
from PyQt5.QtWidgets import (
    QApplication,
    QBoxLayout,
    QButtonGroup,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QShortcut,
    QVBoxLayout,
    QWidget,
)


def add_bool_arg(
        parser: argparse.ArgumentParser,
        name: str,
        default: bool = False,
        help: Optional[str] = None) -> argparse._MutuallyExclusiveGroup:
    """Adds a boolean flag to the given :class:`~ArgumentParser`.
    Parses "natural language" strings as boolean (true, yes, false, no, ...) and
    also accepts flags without values (``--flag`` as true, ``--no-flag`` as
    false).
    Example::
        >>> parser = argparse.ArgumentParser()
        >>> gr = add_bool_arg(parser, "go", default=False)
        >>> parser.parse_args(["--go"]).go
        True
        >>> parser.parse_args(["--no-go"]).go
        False
    """

    def str2bool(val):
        """Parse string as boolean."""
        val = val.lower()
        if val in ("true", "t", "yes", "y", "1"):
            return True
        if val in ("false", "f", "no", "n", "0"):
            return False
        raise ValueError(
            f"Expected type convertible to bool, received `{val}`.")

    name = name.lstrip("-")
    gr = parser.add_mutually_exclusive_group()
    gr.add_argument(
        f"--{name}", nargs="?", default=default, const=True, type=str2bool, help=help
    )
    gr.add_argument(f"--no-{name}", dest=name, action="store_false")
    return gr


def multipoly_to_polys(polygon):
    if isinstance(polygon, list):
        return polygon
    if polygon["type"] == "EmptyPolygon":
        return []
    if polygon["type"] == "MultiPolygon":
        return [
            dict(type="Polygon", coordinates=coordinates)
            for coordinates in polygon["coordinates"]
        ]
    return [polygon]


def sanitize_name(name: str):
    return os.path.basename(name.split("?")[0])


def sanitize_names(names: List[str]):
    return [sanitize_name(name) for name in names]


def merge_results_inplace(results, other):
    for key in other.keys():
        if key not in results:
            results[key] = other[key]
        else:
            for k in other[key]["per_label"].keys():
                if k not in results[key]["per_label"]:
                    results[key]["per_label"][k] = other[key]["per_label"][k]
                else:
                    results[key]["per_label"][k].update(
                        other[key]["per_label"][k])


class App(QMainWindow):
    label_files: List[str]
    image_dir: str
    label_dir: str
    color_map: dict
    label_order: List[str]
    label_scale: int
    title: str
    width: int
    height: int
    left_padding: int
    top_padding: int
    result_data: dict
    result_data_keys: list
    current_labels: list
    current_key: str
    label_qt_obj: dict
    global_layout: QBoxLayout
    label_layout: QBoxLayout
    combine_layout: QBoxLayout
    preview: QLabel
    labels: Dict
    canvas_path: Optional[str]
    auto: bool
    show_next_image_handler = QtCore.pyqtSignal()

    def __init__(
        self,
        label_files: List[str],
        image_dir,
        label_dir,
        color_map,
        label_order: List[str],
        label_scale: int,
        canvas_path: Optional[str],
        auto: bool = False,
    ):
        super().__init__()
        self.label_files = label_files
        self.image_dir = image_dir
        self.label_dir = label_dir
        self.color_map = color_map
        self.label_order = label_order
        self.label_scale = label_scale
        self.canvas_path = canvas_path
        self.auto = auto
        self._init()

    def _init(self):
        self.title = "Label Picker"
        self.left_padding = 10
        self.top_padding = 10
        self.width = 256
        self.height = 400
        self.current_key = ""
        self.label_qt_obj = {}
        self.result_data = {}

        for label_file in self.label_files:
            with open(label_file, "r") as fp:
                data = {
                    sanitize_name(key): value for key, value in json.load(fp).items()
                }
                merge_results_inplace(self.result_data, data)

        # Get all labels there are
        existing_labels = set()
        for item in self.result_data.values():
            existing_labels = existing_labels.union(item["per_label"].keys())
        existing_labels = set(
            label for label in existing_labels if not label.endswith("hole")
        )
        if existing_labels > set(self.label_order):
            print(
                "NOTE: The passed label order (-o) does not contain all "
                "labels specified in the given json(s)."
            )
            print("Given: ", sorted(list(set(self.label_order))))
            print("Found: ", sorted(list(existing_labels)))
            print("Will sleep for 10 seconds before continuing.")
            time.sleep(10)

        self.setWindowTitle(self.title)
        self.setGeometry(self.left_padding, self.top_padding,
                         self.width, self.height)
        self.global_layout = QHBoxLayout()
        self.label_layout = QVBoxLayout()
        self.combine_layout = QVBoxLayout()

        self.global_layout.addLayout(self.label_layout)
        self.global_layout.addLayout(self.combine_layout)
        widget = QWidget()
        widget.setLayout(self.global_layout)
        self.setCentralWidget(widget)
        if not self.auto:
            self.show()

        self.shortcut_next = QShortcut(
            QKeySequence(QtCore.Qt.Key_Return), self)
        self.shortcut_next.activated.connect(self.result_click_callback)

        self.shortcut_undo = QShortcut(
            QKeySequence(QtCore.Qt.Key_Backspace), self)
        self.shortcut_undo.activated.connect(self.undo)

        # Fill a queue of valid 'result_data' indices in a background thread.
        self.ix_queue = Queue()
        self.download_thread = Thread(
            target=self.download_images,
            args=[self.ix_queue],
            daemon=True,
        )
        self.download_thread.start()

        # self.next_image()
        self.show_next_image = True
        self.show_next_image_handler.connect(self.next_image)

        def next_image_thread():
            while True:
                if self.show_next_image:
                    self.show_next_image = False
                    self.show_next_image_handler.emit()
                time.sleep(0.01)

        Thread(target=next_image_thread, daemon=True).start()

    def next_image(self):
        # Wait for new unlabelled images.
        self.previous_key = self.current_key
        self.current_key = ""
        while True:
            try:
                self.current_key = self.ix_queue.get(timeout=1)
            except Empty:
                if self.download_thread.is_alive():
                    continue
                break
            name, path = self.get_current_image()
            if os.path.exists(self.get_label_path()):
                print(f"{path} already labeled, skipping...")
                continue
            break
        # No remaining images.
        if not self.current_key or os.path.exists(self.get_label_path()):
            print("Finished.")
            # Workaround! Image might still be written to disk in the background.
            time.sleep(5)
            sys.exit()

        # Failsafe.
        if not os.path.exists(path):
            raise FileNotFoundError(f"{path} does not exist.")

        print(f"Processing {path}")
        image = Image.open(path)
        self.setWindowTitle(name)

        self.clear_layout(self.label_layout)
        self.labels = defaultdict(dict)
        current_entry = self.result_data[self.current_key]
        self.current_labels = [
            key
            for key in current_entry["per_label"].keys()
            if current_entry["per_label"][key]
        ]

        self.label_qt_obj = {}
        per_label = current_entry["per_label"]
        for name in self.get_current_labels_sorted():
            polygons = per_label[name]["user_polygons"]
            if isinstance(polygons, dict):
                polygons = list(polygons.values())
            polygons = [multipoly_to_polys(polygon) for polygon in polygons]
            if "averaged_polygon" in per_label[name]:
                polygons.append(multipoly_to_polys(
                    per_label[name]["averaged_polygon"]))
            holes = list()
            holekey = [
                key
                for key in per_label.keys()
                if key.startswith(name)
                if key.endswith("hole")
            ]
            if len(holekey) >= 1:
                objects = per_label[holekey[0]]
                holes = objects.get("user_polygons", [])
                if isinstance(holes, dict):
                    holes = list(holes.values())
                holes = [multipoly_to_polys(polygon) for polygon in holes]
                if "averaged_polygon" in objects:
                    holes.append(multipoly_to_polys(
                        objects["averaged_polygon"]))

            label_qt_obj = {}
            layout = QHBoxLayout()
            buttons = [QPushButton() for _ in range(len(polygons))]
            button_group = QButtonGroup(self)
            button_group.exclusive = True
            self.init_buttons(buttons, button_group, layout)
            self.label_layout.addLayout(layout)

            label_qt_obj["layout"] = layout
            label_qt_obj["buttons"] = buttons
            label_qt_obj["button_group"] = button_group
            self.label_qt_obj[name] = label_qt_obj

            pairs = zip_longest(
                reversed(polygons),
                reversed(holes),
                fillvalue=[],
            )
            for ix, (objects, masks) in enumerate(list(pairs)[: len(polygons)]):
                overlay = self.get_label_canvas(image.size)
                objects = [list(map(tuple, x["coordinates"][0]))
                           for x in objects]
                masks = [list(map(tuple, x["coordinates"][0])) for x in masks]
                self.draw_polygons(name, overlay, objects, masks)
                label = overlay.copy()
                self.labels[name][ix] = label
                labeled_overlay = self.overlay_image(image, overlay)
                qim = ImageQt.ImageQt(labeled_overlay)
                pixmap = QPixmap.fromImage(
                    qim).scaledToHeight(self.label_scale)
                icon = QIcon(pixmap)
                button = self.label_qt_obj[name]["buttons"][ix]
                button.setIcon(icon)
                button.setIconSize(pixmap.rect().size())

        self.preview = QLabel(self)
        pixmap = QPixmap(path).scaledToHeight(512)
        self.preview.setPixmap(pixmap)
        self.clear_layout(self.combine_layout)
        self.combine_layout.addWidget(self.preview)
        self.preview.mousePressEvent = self.result_click_callback

        self.label_press_callback()  # draw preselected annotations

        # Automatically continue with default selection when in auto mode.
        if self.auto:
            self.result_click_callback()

    def result_click_callback(self, e=None):
        selection = {}
        all_selected = True

        for label in self.get_current_labels_sorted():
            selected = False
            for i, button in enumerate(self.label_qt_obj[label]["buttons"]):
                if button.isChecked():
                    selected = True
                    selection[label] = i

            if not selected:
                all_selected = False

        if all_selected:
            self.save_label(selection)
            self.show_next_image = True

    def undo(self):
        path = self.get_label_path(self.previous_key)
        try:
            os.remove(path)
        except OSError:
            pass
        else:
            print(f"Deleted {path}")
            self.ix_queue.put(self.previous_key)

    def label_press_callback(self):
        name, path = self.get_current_image()
        combined = Image.open(path)

        for label in self.get_current_labels_sorted():
            for i, button in enumerate(self.label_qt_obj[label]["buttons"]):
                if button.isChecked():
                    overlay = self.labels[label][i]
                    labeled_overlay = self.overlay_image(combined, overlay)
                    qim = ImageQt.ImageQt(labeled_overlay)
                    pixmap = QPixmap.fromImage(qim).scaledToHeight(512)
                    self.preview.setPixmap(pixmap)
                    combined = labeled_overlay
        self.preview.repaint()

    def get_current_image(self):
        name = os.path.basename(self.current_key)
        path = os.path.join(self.image_dir, name)
        return name, path

    def get_label_path(self, key=""):
        if not key:
            key = self.current_key
        name = os.path.basename(key)
        extension = str(name.split(".")[1])
        png = name.replace(extension, "png")
        path = os.path.join(self.label_dir, png)
        return path

    def get_label_canvas(self, size):
        if self.canvas_path is None:
            return Image.new("RGBA", size, color=(255, 255, 255, 0))
        name, extension = os.path.basename(self.current_key).split(".")
        png = f"{name}_annotate.png"
        path = os.path.join(self.canvas_path, png)
        img = Image.open(path).convert("RGBA")
        img = np.array(img)
        img[np.all(img[..., :-1] == 255, axis=-1), -1] = 0
        return Image.fromarray(img)

    def get_current_labels_sorted(self):
        sorted_labels = []
        for label in self.label_order:
            if label in self.current_labels:
                sorted_labels.append(label)
        return sorted_labels

    def save_label(self, selection):
        _, path = self.get_current_image()
        final = Image.new("RGBA", Image.open(path).size, color="#ffff")
        for label in self.get_current_labels_sorted():
            label_img = self.labels[label][selection[label]]
            final = self.overlay_image(final, label_img)
        final.save(self.get_label_path())
        print("Saved", self.get_label_path())

    def draw_polygons(
        self,
        label_type: str,
        img: Image,
        objects: List[List[Tuple[float, float]]],
        masks: List[List[Tuple[float, float]]],
    ) -> None:
        overlay = Image.new("RGBA", img.size, color=(255, 255, 255, 0))
        drawer = ImageDraw.Draw(overlay)
        for points in objects:
            drawer.polygon(points, fill=self.color_map[label_type])
        for points in masks:
            drawer.polygon(points, fill=(255, 255, 255, 0))
        img.paste(overlay, (0, 0), overlay)

    def download_images(self, ix_queue: Queue):
        keys = list(self.result_data.keys())
        for ix, key in enumerate(keys):
            data = self.result_data[key]
            name = os.path.basename(key)
            dst = os.path.join(self.image_dir, name)
            verified = False
            if os.path.exists(dst):
                verified = True
                try:
                    Image.open(dst).putalpha(255)
                except Exception:
                    verified = False
            if not verified:
                print(
                    f"Downloading image {ix} of {len(self.result_data)}",
                    end="\r",
                )
                retries = 10
                for retry in range(retries):
                    try:
                        urllib.request.urlretrieve(data["image_url"], dst)
                    except BaseException as err:
                        if retry == (retries - 1):
                            print("Failed:", data["image_url"])
                            raise err
                    else:
                        break
            ix_queue.put(key)

    def init_buttons(self, buttons, group, layout):
        for idx, button in enumerate(buttons):
            button.setCheckable(True)
            button.setChecked(idx == 0)
            group.buttonClicked[int].connect(self.label_press_callback)
            group.addButton(button, idx)
            layout.addWidget(button)

    def clear_layout(self, layout):
        if layout is not None:
            while layout.count():
                child = layout.takeAt(0)
                if child.widget() is not None:
                    child.widget().deleteLater()
                elif child.layout() is not None:
                    self.clear_layout(child.layout())

    @staticmethod
    def overlay_image(image, overlay):
        joined = image.copy()
        joined.paste(overlay, (0, 0), overlay)
        return joined


if __name__ == "__main__":
    app = QApplication(sys.argv)

    parser = argparse.ArgumentParser(
        description="Pick the best label from a collection of labels.",
    )
    parser.add_argument(
        "-f",
        "--label_files",
        type=str,
        nargs="+",
        help="Label file(s) (QM format) in JSON",
    )
    parser.add_argument(
        "-i",
        "--image_path",
        type=str,
        help="Directory to store images",
    )
    parser.add_argument(
        "-l",
        "--label_path",
        type=str,
        help="Directory to store final labels",
    )
    parser.add_argument(
        "-c",
        "--color_map",
        type=str,
        help="Mapping from label type to RGB color, e.g."
        "{'claw': '255, 0, 0', 'truck': '0, 255, 0'}",
    )
    parser.add_argument(
        "-o",
        "--label_order",
        type=str,
        help="Drawing order of labels, e.g. 'truck, logs, claw'",
    )
    parser.add_argument(
        "-s",
        "--label_scale",
        type=int,
        default=256,
        help="Height scale of labeled image",
    )
    parser.add_argument(
        "--canvas_path",
        type=str,
        default=None,
        help="Label base canvas, new labels are added on top of these canvas images.",
    )
    add_bool_arg(
        parser,
        name="auto",
        default=False,
        help="Whether to auto accept preselection.",
    )
    args = parser.parse_args()

    color_map_json_str = args.color_map.replace("'", '"')
    color_map_json = json.loads(color_map_json_str)
    color_map = {}
    for label_type, color_string in color_map_json.items():
        splits = color_string.split(",")
        if len(splits) != 3:
            raise ValueError("Not a valid color mapping!")

        color_map[label_type] = (int(splits[0]), int(
            splits[1]), int(splits[2]), 255)

    label_order = list(map(lambda x: x.strip(), args.label_order.split(",")))

    os.makedirs(args.image_path, exist_ok=True)
    os.makedirs(args.label_path, exist_ok=True)

    ex = App(
        label_files=args.label_files,
        image_dir=args.image_path,
        label_dir=args.label_path,
        color_map=color_map,
        label_order=label_order,
        label_scale=args.label_scale,
        canvas_path=args.canvas_path,
        auto=bool(args.auto),
    )
    sys.exit(app.exec_())
