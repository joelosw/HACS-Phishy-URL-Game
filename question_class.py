import cv2
import numpy as np
import urllib
from urllib.parse import urljoin
import random
import os
from typing import Tuple
from PIL import Image

random_words = 'personal index home account language start login logout organization legal calendar' + \
    'network cloud estonia ee device  security office'

symbols = ['-', '.', '_']


class Question():
    logo_file: Image
    real_url: str

    def __init__(self, logo_path, true_url, logo_size: Tuple[int, int] = None):
        super().__init__()
        self.logo_file = Image.open(logo_path)
        self.real_url = true_url

    @ property
    def random_false_url(self):
        url_split = self.real_url.split('.')
        host_split = url_split[-2].split('/')
        host = host_split[-1]
        insert_index = random.randint(1, len(host) - 1)
        insert_symbol = random.choice(symbols)
        new_name = list(host)
        new_name.insert(insert_index, insert_symbol)
        new_name = ''.join(new_name)
        if len(url_split) > 2:
            new_name = '.' + new_name
        host_split[-1] = new_name + '.'
        host_name = ''.join(host_split)
        url_split[-2] = host_name
        url = ''.join(url_split)
        url = url + '/' + random.choice(random_words.split(' '))
        return url


if __name__ == '__main__':
    q1 = Question('logos/facebook.png', 'http://facebook.com')
    print(q1.random_false_url)
