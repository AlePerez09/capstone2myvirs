# Limitations

**MyVIRS Team A** · Sprint 5 · November 2026

What our system does not do, or does not do well, stated plainly. Each
item says what it affects. Where a number is given, it comes from our own
evaluation (`evaluation_report.md`, `evaluation/RESULTS.md`).

## 1. Our main idea is not proven yet

- **The combined ranking did not beat frequency alone.** In our Sprint 4
  evaluation, mixing relevance with the VIRS frequency band ranked CK-12
  lesson vocabulary *worse* than frequency alone on Biology (average
  precision 0.143 vs. 0.164, significant) and lower on Trigonometry
  (0.162 vs. 0.192, not significant). The criterion we set in advance was
  not met.
  *Affects:* we can't claim the default ranking picks better words to
  teach than a simple frequency list.
- **What did beat frequency doesn't depend on relevance.** A setting that
  counts words within the lesson and drops number words and generic verbs
  beat frequency on both books, but it did slightly better with relevance
  turned off.
  *Affects:* the relevance part (TextRank) has not been shown to add value
  on its own.

## 2. How we measured has its own limits

- **The answer key favors frequency.** We used each CK-12 lesson's
  Vocabulary list as the "right answers." Those are words the book repeats
  on purpose, so counting does well by design.
- **No expert or learner judgments.** Professor Dwyer's top-ten picks,
  planned as a second answer key, weren't collected, and no students or
  teachers have used the system.
- **Only the first word of multiword terms is checked** ("nitrogen" from
  "nitrogen cycle"), which gives odd keys like *include* from
  "included angle."
- **Two CK-12 books only,** and Trigonometry has just 22 lessons.

*Affects:* our results say how well the system matches CK-12's glossary
terms, not whether it helps people learn.

## 3. What text it can read

- **Typed PDFs and plain text only.** Scanned pages and handwriting are
  rejected, because there's no OCR (text recognition).
- **Some PDFs come out with missing spaces.** The CK-12 Trigonometry text
  extracted as run-together words ("willreviewsomeimportantaspects"). We
  repaired it for the evaluation with a separate script, but the pipeline
  itself doesn't detect or fix this.
- **English only.** The language model, stop words, and word lists are
  all English.
- **Tested on CK-12 textbooks only.** The rules that remove section
  numbers, page footers, and "Figure 2.4" labels were written for CK-12's
  layout and may miss other publishers' formats.

*Affects:* uploading a worksheet photo, a non-English text, or a PDF from a
different publisher may fail or give noisy results.

## 4. How it handles words

- **Word families come from rules, not the authors' lists.** We group
  forms with spaCy lemmas plus conservative suffix and prefix rules.
  Nouns ending in *-er* (*walker*) and irregular forms (*decision* →
  *decide*) aren't grouped, and some groupings may differ from how Eric's
  research counted families.
- **No phrases.** Entries like "in spite of" or "law of sines" are split
  into single words.
- **Names can slip through** as ordinary nouns (people, places, brands).
- **Number words hurt the score.** At the Product Owner's request,
  numbers are spelled out and kept ("forty-five," "hundred"). They're
  common and well connected, so they crowd the top of the list. They stay
  on by default until the team and Product Owner decide otherwise.
- **Generic textbook verbs rank too high** (*include, find, produce,
  occur*). An optional filter removes some, not all.
- **Each word gets one part of speech**, its most common one in the text,
  so *use* as a noun and as a verb are treated alike.
- **No known open bugs.** The two found in Sprint 4 (a one-word passage
  getting relevance 0, and forms like *explained* or *sections* slipping
  past the layout-word filter) were fixed in Sprint 5 (pull request #5),
  and their tests now pass.

## 5. The word list

- **The VIRS list's source can't be fully confirmed.** `data/virs_words.csv`
  (30,259 words) was saved by a Team B member from the capstone site before
  it was removed. We haven't checked it against Professor Dwyer's original
  Excel files.
- **Nearly half the words are in the HIGH band** (14,174), so the band
  doesn't separate words much. Our evaluation found it's the weakest part
  of the ranking.
- **Gaps:** no number words and no phrases; only 2,733 words have a grade
  level; STEM words aren't split into math and science.
- **The loader for Eric's Excel files has only been tested on mock files**
  built from a description of their layout. It may need fixes when the real
  files arrive.

*Affects:* bands, subjects, and grade levels shown to teachers are only as
accurate as this list.

## 6. The ranking settings

- **The 50/50 weights and band scores were chosen, not tuned.** They were
  fixed before the evaluation on purpose, and the evaluation showed they
  don't work well.
- **Relevance is measured within one text at a time.** A word's score
  depends on that passage alone, so short passages give less reliable
  scores than whole chapters.
- **The better-performing options aren't the default yet.** In-lesson
  counting, keyness, and subject-aware relevance are still in an open pull
  request, and the team hasn't agreed with the Product Owner on a new
  default.

## 7. Running and using it

- **Team B's app doesn't call our code yet.** They can read our sample
  JSON output, but there's no live connection or web service between
  the two systems.
- **Setup needs Python and an internet connection.** `setup.bat` or
  `setup.sh` installs everything in one step, but you need Python 3.10 to
  3.13 already installed, and the first install downloads about 100 MB.
  Versions have minimums and spaCy is held to 3.8, so a future package
  release could still break something.
- **Nothing is stored and no one signs in.** The system doesn't save
  uploaded texts, learn from new material, or track individual learners.
  Collecting learner data was outside this semester's rules.
- **Not deployed.** It runs from the command line on a developer's computer.

## What it is not meant for

- It is **not a measure of a student's reading level or ability**.
- It does **not personalize** word lists to a learner's history.
- Its rankings are **suggestions for a teacher to review**, not a final
  list of words students must learn.
