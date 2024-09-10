#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os

from pycorrector import Corrector
from pycorrector.macbert.macbert_corrector import MacBertCorrector
from pycorrector import ConfusionCorrector

class RepoTypoDetector:

    def __init__(self, repo_path: str):
        self.repo_path = repo_path
        # self.corrector = Corrector()
        self.corrector = MacBertCorrector()

    def scan(self):
        for root, dirs, files in os.walk(self.repo_path):
            for name in files:
                filepath = os.path.join(root, name)
                try:
                    self.scan_single_file(filepath)
                except Exception as e:
                    print(e)
            # for name in dirs:
            #     print(os.path.join(root, name))

    def scan_single_file(self, filepath):
        """
        扫描单个文件
        :param filepath:
        :return:
        """
        with open(filepath, 'r', encoding='utf-8') as file:
            content = file.read()
            # 返回结果样例：
            # [
            #     {
            #         "source": "少先队员因该为老人让坐",
            #         "target": "少先队员应该为老人让座",
            #         "errors": [
            #             4,
            #             10
            #         ]
            #     }
            # ]
            # results = self.corrector.correct_batch([content])
            results = self.corrector.macbert_correct(content)
            for result in results:
                # 如果没有错误的话忽略即可
                if len(result['errors']) == 0:
                    print(f'${filepath} is ok')
                    pass
                else:
                    print(result)


if __name__ == '__main__':
    detector = RepoTypoDetector('/Users/cc11001100/github/nacos')
    detector.scan()
