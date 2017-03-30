==============
Design choices
==============

.. contents:: :local:

Introduction
============

In this chapter we explain some design choices made in the smart contracts.

Timestamp vs. block number
==========================

The code uses block timestamps instead of block numbers for start and events. We work on the assumption that crowdsale periods are not so short or time sensitive there would be need for block number based timing. Furthermore if the network miners start to skew block timestamps we might have a larger problem with dishonest miners.

Crowdsale strategies and compound design pattern
================================================

Instead of cramming all the logic into a single contract through mixins and inheritance, we assemble our crowdsale from multiple components. Benefits include more elegant code, better reusability, separation of concern and testability.

Mainly, our crowdsales have the following major parts

* Crowdsale core: capped or uncapped

* Pricing strategy: how price changes during the crowdsale

* Finalizing strategy: What happens after a successful crowdsale: allow tokens to be transferable, give out extra tokens, etc.

Background information
======================

* https://drive.google.com/file/d/0ByMtMw2hul0EN3NCaVFHSFdxRzA/view
