# Ken French International 25 Portfolios (Daily) — regional panels

Source: Ken French Data Library
(https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html).

- `Japan_25_Portfolios_ME_BE-ME_Daily.csv` — from
  `Japan_25_Portfolios_ME_BE-ME_daily_CSV.zip`, built from the 202605
  Bloomberg database (file header), downloaded 2026-07-20.
  sha256 (csv): b14835fa67e270b5021919d8ca97892cb8060a56b97fec293698eba79b0512eb
  sha256 (zip): b6b2ad6f43e29e8f997914a7acece38f9ca155bcfc80e21e72a92a0b3ec7e8b0
  Coverage 1990-07-02 – 2026-05-29; 25 ME x BE/ME value- and
  equal-weighted daily returns; missing values coded -99.99.

Used by `code/e_japan.py` under the E-R regional register
(PREREG_FRENCH49.md, PRE-REGISTRATION E) as operationalized by
Addendum L (2026-07-20, commit dfd9fe7, lodged before any run touched
this data). Only the "Average Value Weighted Returns -- Daily" block is
consumed. This is exactly the panel family the E-R register lodged
("the French international daily 25-portfolio panels"); no substitution.
