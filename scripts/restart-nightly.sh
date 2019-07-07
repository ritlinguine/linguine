#!/usr/bin/env bash

systemctl restart linguine-corenlp
systemctl restart linguine-node
systemctl restart linguine-python
systemctl restart linguine-sphinx
systemctl restart mongod
