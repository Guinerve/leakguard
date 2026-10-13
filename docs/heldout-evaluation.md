# Held-out evaluation (2026-10-13)

`docs/recall-on-documented-leaks.md` measured recall on 7 leaks, and I then wrote LG008 after reading one of them, so
that set is no longer independent. This is a second set nobody tuned leakguard against: 42 labelled files from
three sources leakguard had never been run on (corpus and licences: `eval/heldout/README.md`).

## Protocol (written before the first run)

1. **Corpus frozen first.** Files and labels were collected, hashed into `eval/heldout/labels.json`, and this
   protocol was written before leakguard was run on any of them. Labels come from the sources, not from me: the
   ASE'22 authors' expected results (`test_preprocessing.py`, `test_overlap.py`), the article's own "this is the
   look-ahead bias" / "walk-forward fix" framing, and scikit-learn's official examples taken as clean.
2. **One run, no tuning.** The rules are the ones in the working tree at the time of the run (after the
   multi-split and notebook fixes, which were built and tested on my own fixtures). No rule is changed between the
   run and this report. A rule written later because of something seen here makes that file in-sample, and it must
   be reported that way.
3. **Unit: one file.** A leaky file counts as **caught** only if at least one finding points at the documented
   leak (the fit or statistic whose output reaches the evaluation data, the resampling before the split, the fit on
   the full series). A finding somewhere else in a leaky file does not count as catching it.
4. **Clean files.** Any finding in a clean file is a **false positive** by label. If reading the code shows the
   finding is a real problem the label missed, it is still counted as a false positive here, and noted.
5. **Extra findings** in leaky files that don't point at the documented leak are listed and judged by reading.
   ASE'22 files labelled only for overlap leakage have no preprocessing label, so findings there are judged by
   reading and kept out of the totals.
6. A file leakguard cannot parse counts as **missed**.

Reproduce: `uv run python eval/fetch_marketcalls.py && uv run python eval/run_heldout.py`.

## Results

(Filled in after the run.)
