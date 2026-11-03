#!/bin/bash

# Create the animated gif.

# We use 'convert' from ImageMagick

set -xe

convert -delay 300 -loop 0 anim_step*.png anim.gif
