# Incorrect Penalty Challenges for CTFd

This CTFd plugin creates a challenge type which awards a penalty of `penalty`
points for each failed attempt. The total penalty for a given challenge can be
capped by setting `max_penalty` to something other than 0.

The code is based off of the dynamic_challenges plugin that is included in CTFd.

# Installation

**REQUIRES: CTFd >= v3.0.0**

1. Clone this repository to `CTFd/plugins`. It is important that the folder is
   named `incorrect_penalty_challenges` so CTFd can serve the files in the `assets`
   directory.
