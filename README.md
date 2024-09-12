# Incorrect Penalty Challenges for CTFd

This CTFd plugin creates a challenge type which awards a penalty for the number
of failed attempts when the challenge is solved. The total penalty is
`-(penalty * failures)`, with a cap such that the challenge will not be worth
less than `minimum` points.

The code is based off of the dynamic_challenges plugin that is included in CTFd.

# Installation

**REQUIRES: CTFd >= v3.0.0**

1. Clone this repository to `CTFd/plugins`. It is important that the folder is
   named `incorrect_penalty_challenges` so CTFd can serve the files in the `assets`
   directory.
