---
title: Quantum chromodynamics
short_title: QCD
order: 1
summary: >-
  The theory of the strong force and how quarks and gluons become the jets
  and hadrons seen in detectors, built into the PYTHIA event generator.
# image: my-photo.jpg      # optional header photo, saved in research/images/
leads: [peter-skands]
links:
  - title: PYTHIA event generator
    url: https://pythia.org/
---

Quantum chromodynamics (QCD) describes how quarks and gluons interact through
the strong force. At the LHC almost every collision is dominated by QCD. Outgoing
quarks and gluons radiate further gluons, forming sprays of particles
called *jets*. Eventually they bind into the protons, pions and other hadrons that
detectors actually see. This last step is called *hadronisation*.

## Simulating collisions

Many of these processes cannot be calculated exactly, so the group builds detailed
models of them and uses Markov-chain Monte Carlo methods to sample the
quantum-mechanical probability distributions. The result is a "virtual
collider": a program that produces realistic simulated collisions,
one event at a time.

Monash is a core developer of **PYTHIA**, one of the most widely used
programs in particle physics. Nearly every LHC analysis relies on it. Our
work includes:

- **Parton showers** and the VINCIA antenna shower: the radiation patterns of
  high-energy quarks and gluons,
- **Hadronisation** and colour strings: how confinement turns quarks into hadrons,
- **Tuning and validation**: comparing simulations to data. The widely used
  "Monash tune" of PYTHIA 8 was developed here.

We are part of the PYTHIA, MCnet and LHC@home collaborations.
