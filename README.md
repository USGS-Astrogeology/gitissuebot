# Git Issue Bot

This repository stores an issue bot for working with GitHub issues via the GraphQL API. Right now, 
the bot is setup to query the issues, and find issues that are >6 months, >11 months, and >12 months in age.
Issues are then labelled as `inactive` with a notice, pinged to become active, and closed with an
`automatically_closed` label respectively.

Right now, the query in main.py is set to only pull the last:1 issue. This should be modified locally
before running the bot as each query does count against the API limits.

