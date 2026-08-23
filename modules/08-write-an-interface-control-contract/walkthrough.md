# Walkthrough: Write an Interface Control Contract

1. Read the exact guiding question, then connect P06's logical scalar input and P07's value-plus-quality gate to the need for endpoint agreement.
2. Predict once whether a plausible 0.524 can be accepted as degrees when its producer declares radians.
3. Run `experiment.m` and inspect only the eight baseline clause results. Name the producer and receiver obligation behind each bar.
4. Inspect the separate degree-valued view and explain why exact value preservation is a compatibility fact, not P06 execution.
5. In `interactive.m`, reset and move only source angle to -180, +180, and +180.001 deg. Observe inclusive limits and just-outside rejection.
6. Read the range mechanism, then reset before touching record shape.
7. Move declared payload length to five, six, and seven words. Explain why only six is interpretable without guessing.
8. Reset, then try sender versions 0, 1, and 2. Distinguish explicit compatibility from accidental similarity.
9. Inject wrong identity, checksum corruption, invalid quality code, and sequence overflow one at a time. Name the first failed clause.
10. Clear faults and uncheck source quality. Observe a conformant accepted record whose scalar remains withheld.
11. Inject cancellation, timeout, and their tie. Confirm that no payload arrives and no clause is evaluated; state what elapsed-time facts remain unknown.
12. Inject unit mismatch under complete validation. Observe the radian value and strict rejection.
13. Select broken value-only validation. Compare conformance, receiver acceptance, release, and semantic error, then explain the false acceptance mechanism.
14. Restore complete validation and all baseline controls to demonstrate stateless recovery.
15. Run `run_checks.m`, answer `checks.md` one prompt at a time, and teach back the agreement mechanism and consequence.
