import random
import logging
from typing import Tuple
from PIL import Image
logging.basicConfig(encoding='utf-8', level=logging.INFO)
logger = logging.getLogger('Question')


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
        logger.info('Loading Image {}'.format(logo_path))
        self.logo_file = Image.open(logo_path).convert('RGBA')
        self.real_url = true_url

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

        logger.debug('Altering Question in mode {}'.format(mode))

        (original_url, prefix) = self.remove_protocol(self.real_url)
        url_split = original_url.split('.')

        if mode == 1:
            # Randomly insert a punctuation in the hostname
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
            # Randomly insert a word as new hostname
            url_split.insert(-1, random.choice(random_words.split(' ')))

        elif mode == 3:
            # Randomly define wether to repeat or skip one character:
            host_name = url_split[-2]
            if random.random() <= 0.5:
                # Repeat one character randomly
                # 1. Get characteer
                c = random.choice(host_name)
                # 2. Find where character appears in word
                idx = host_name.find(c)
                # 3. re-insert character at same place as original character
                host_name_list = list(host_name)
                host_name_list.insert(idx, c)
                host_name = ''.join(host_name_list)

            else:
                # delete one character randomly
                idx = random.randint(0, len(host_name) - 1)
                host_name = [x for i, x in enumerate(host_name) if i != idx]
                host_name = ''.join(host_name)
            url_split[-2] = host_name
        url = '.'.join(url_split)
        url = prefix + url + '/' + random.choice(random_words.split(' '))
        logger.debug('Generated URL {} in mode {}'.format(url, mode))
        return url

    def remove_protocol(self, url) -> Tuple[str, str]:
        """
        helper function to remove http:// - like protocol in front of the url.

        Returns
        -------
        Tuple[str, str]
            (url without protocol, protocol)
        """
        original_url = url
        prefix = ''
        if "https://" in original_url:
            prefix = "https://"
            original_url = original_url.replace("https://", "")
        elif "http://" in original_url:
            prefix = "http://"
            original_url = original_url.replace("http://", "")
        return (original_url, prefix)

    def random_correct_url(self) -> str:
        """
        Generate a random URL that is still valid.
        It just randomly adds paths (/.../...) and subdomains to the url.

        Returns
        -------
        str
            the random, valid url
        """
        (original_url, prefix) = self.remove_protocol(self.real_url)
        url_split = original_url.split('.')
        r_words = random_words.split(' ')
        if len(url_split) > 2:
            r_words = r_words + url_split[:-2]
            url_split = url_split[-2:]
        num_random_words = random.randint(0, 2)
        add_words = random.sample(r_words, k=num_random_words)
        [url_split.insert(-2, word) for word in add_words]
        url = prefix + '.'.join(url_split)
        return url


if __name__ == '__main__':
    q1 = Question('logos/Bolt.png', 'http://www.facebook.com')
    # for i in range(150):
    #     print(q1.random_false_url())
