#!/bin/bash

options="$1"

this_folder=$(dirname $(readlink -f "${BASH_SOURCE[-1]}"))
parent_folder=$(dirname ${this_folder})

py.test --cov="$parent_folder" --ignore="${parent_folder}/docs" ${options}

# https://github.com/pytest-dev/pytest/issues/913#issuecomment-387969212
exit $?
