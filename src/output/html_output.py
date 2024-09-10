#!/usr/bin/env python3
# -*- coding: utf-8 -*-

class HtmlOutput:

    def __init__(self, result: object):
        self.result = result

    def write(self, filepath):
        pass

    def render(self) -> str:
        parts = ['<html><head></head><body>']
        parts.append('')
