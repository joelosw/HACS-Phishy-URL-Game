import cv2
import numpy as np
import urllib
from urllib.parse import urljoin
import random
import os
from typing import Tuple
from PIL import Image

random_words = 'personal index home account language start login logout organization legal calendar' + \
    ' network cloud estonia ee device security office'

symbols = ['-', '.', '_']


class Question():
    """
    Class representing one question. This includes a logo file as well as the true url.
    False urls are then generated randomly with different possible altering-methods. 

    """
    logo_file: Image
    real_url: str

    def __init__(self, logo_path: str, true_url: str):
        """
        Generate one new question instance. 

        Parameters
        ----------
        logo_path : path to logo-file
        true_url : true url contianing at least host.tld
        logo_size : Tuple[int, int], optional
            [description], by default None
        """
        super().__init__()
        self.logo_file = Image.open(logo_path)
        self.real_url = true_url

    @ property
    def random_false_url(self, mode: int = None) -> str:
        """Generate a random, false URL

        Parameters
        ----------
        mode: int  which mode to use to modify random urls:
        1: Enter random punctuation mark
        2: Insert new hostname after tru name
        3: Typo-Attack: repeat or miss one letter #### NOT IMPLEMENTED YET#####

        Returns
        -------
        str
            the false, phishy url
        """

        if mode is None:
            mode = random.randint(1, 3)

        (original_url, prefix) = self.remove_protocol()
        url_split = original_url.split('.')

        if mode == 1:
            host_split = url_split[-2].split('/')
            host = host_split[-1]
            insert_index = random.randint(1, len(host) - 1)
            insert_symbol = random.choice(symbols)
            new_name = list(host)
            new_name.insert(insert_index, insert_symbol)
            new_name = ''.join(new_name)

            host_split[-1] = new_name
            host_name = ''.join(host_split)
            url_split[-2] = host_name
        elif mode == 2:
            url_split.insert(-1, random.choice(random_words.split(' ')))

        elif mode == 3:
            print('ATTENTION MODE 3 NOT IMPLEMENTED YET')

        url = '.'.join(url_split)
        url = prefix + url + '/' + random.choice(random_words.split(' '))
        return url

    def remove_protocol(self) -> Tuple[str, str]:
        """
        helper function to remove http:// - like protocol in front of the url.

        Returns
        -------
        Tuple[str, str]
            (url without protocol, protocol)
        """
        original_url = self.real_url
        prefix = ''
        if "https://" in original_url:
            prefix = "https://"
            original_url = original_url.replace("https://", "")
        elif "http://" in original_url:
            prefix = "http://"
            original_url = original_url.replace("http://", "")
        return (original_url, prefix)

    @property
    def random_correct_url(self) -> str:
        """
        Generate a random URL that is still valid.
        It just randomly adds paths (/.../...) and subdomains to the url.

        Returns
        -------
        str
            the random, valid url
        """
        (original_url, prefix) = self.remove_protocol()
        url_split = original_url.split('.')
        r_words = random_words.split(' ')
        if len(url_split) > 2:
            r_words = r_words + url_split[:2]
            url_split = url_split[-2:]
        num_random_words = random.randint(0, 3)
        add_words = random.sample(r_words, k=num_random_words)
        [url_split.insert(-2, word) for word in add_words]
        return prefix + '.'.join(url_split)


if __name__ == '__main__':
    q1 = Question('logos/facebook.png', 'http://www.facebook.com')
    print(q1.random_false_url)
