#!/usr/bin/python3

import json
from zipclean import clean_guide
import pprint

class Test_clean_guide:

    def setUp(self):
        guide_path = "./testguides/test_guide.json"
        self.guide_data = None
        with open(guide_path,'r') as guide:
            self.guide_data = json.load(guide)


        expected_path_remove_1 = "./testguides/expected_remove_zipcodes.json"
        self.expected_data_1 = None
        with open(expected_path_remove_1,'r') as guide:
            self.expected_data_1 = json.load(guide)


        return

    def test_remove_zipcodes(self):
        """
        remove zipcodes from addresses and leaves everything else intact.
        """

        frequency = 2
        clean_data = clean_guide(self.guide_data, frequency)

        assert clean_data == self.expected_data_1
        return


