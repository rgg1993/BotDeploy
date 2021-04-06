#!/usr/bin/env python3
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import os

""" Bot Configuration """


class DefaultConfig:
    """ Bot Configuration """

    PORT = 3978
    APP_ID = os.environ.get(
        "MicrosoftAppId", "3581a0c7-8f2a-4474-8300-bb11a812a4ae")
    APP_PASSWORD = os.environ.get(
        "MicrosoftAppPassword", "BMKk_V.r~q8znOH7_YdwOp~948OE99253o")
