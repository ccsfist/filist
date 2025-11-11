# This is a repo for FI links serving # filinks

### Immediate next steps:
  - this version is a transition version
      - it has the old multiple csv file in multifile directory
      - it has a new single csv file format in singlefile directory, and has script2combinedcsv directory with the python script I used to merge into 1 csv
      - next version will have google tracking
      - need to add features to include new pubs, look for duplicates across merged csv file, keep image cache working with new documents
      - forcerank column in csv file that allows you to have items sit near the top of the html, irregardless of the date

### It has a few pieces.
  - make_fihtml.py 
    uses media_data.csv, news_data.csv, publications_data.csv 
    to generate: financial_instruments.html
    This is a list based on https://iri.columbia.edu/topics/financial-instruments/
    The *_data.csv files were provided by Jeff Turmelle, and edited slightly to fix errors, have news sources, etc.

    the python script has a "cache" option, which I am using for when the IRI website goes down.  
    It creates a cache directory and when activated makes the html point to the cache
    It needs to be thought through (and perhaps not sit in the repo, but be more of a backup)

### Only needed to migrate out of old IRI page:
  - scrape_images.py
    scrapes https://iri.columbia.edu/topics/financial-instruments/
    generates image_data.csv and a directory of cached images called images
    Should only need to be run the first time Im pulling from the IRI website
 - images2news_data.py
   This takes the images scraped above, and adds them to a imagename column in the news_data.csv file.
 
### Now make_fihtml.py code is updated to use imagename column in the news_data.csv to look for images
   - The way to add an image will be to put it in the images folder, and point to it in the news_data.csv file

  - find_duplicates.py
    this searches the 3 csv files for potential duplicates and reports them to stdout
    Some of these are not duplicates, but simply have the same title words
  
### I need to:
  - add tracking
  - update wiiet links to our repo, include pdf, spreadsheet
    It is already a repo: git@bitbucket.org:jturmelle/wiiedu.git
   Jeff has moved it to https://github.com/ccsfist 
    I changed it to be directly hosted on github.io
  - check for broken links, decide what to do
  - make sure everything is cached, if only backups
  - make a version that can create short lists of stuff for donors/partners
  - figure out where to host for real version
  - Columbia commons emailed ac@columbia.edu asking about their many APIs, 
    - They pointed me to https://urldefense.com/v3/__https://web.archive.org/web/20250902075915/https:/*petstore.swagger.io/?url=https*3A*2F*2Facademiccommons.columbia.edu*2Fapi*2Fv1*2Fswagger_doc**Asearch*getApiV1Search__;LyUlJSUlJSMvLw!!BDUfV1Et5lrpZQ!XaGbAEYpw_F7_QZWvuzJ01LiZjHq_YjpN45ATbGrcxIEYG1TKBd7yaxea2JcQ6HbusgSUC-9B02RXC2lfD5WTbVo$
    - the query (from gemini) seems to give me all the info I need to generate a csv
      - https://academiccommons.columbia.edu/api/v1/search?q=Daniel+Osgood&per_page=100&page=1
      - do this query manually in your browser (until it is set up automatically)
      - save this to academic.json then...
    -  python add_commons2publications.py
      - updates publications csv,
      - replaces existing links (based on title)
      - does not find duplicates!
      - find_pubdup.py should allow you to find duplicates, and pick which items you want to keep
        - note that academic commons hides journals, so probably want to keep a mix of them
      - keep copy of original publications data
      - until this is cleaned up, you need to
        - python add_commons2publications.py
        - python find_pubdup.py
        - cp publications_data_deduped.csv publications_data.csv
        - python make_fihtml.py
        - cp financial_instruments.html index.html
  - Use ai to figure out which are not public domain, strategically use iri server with password. 
  - formatting?
  - Make category that hovers near the top always?

### Things for simplifying operational version
  - make find_pubdub.py write over publications file, allow it to pick an entire option (instead of only all the fields one by one)
    - make pubdub work for combined csvs, have file that saves ones that are NOT duplicates
  - combine media_data.csv, news_data.csv, publications_data.csv into a single csv file
  - make it save to index.html instead of financial_instruments.html
  - clean up add_commons2publications, make_fihtml workflow
  - auto download to academic commons json file?
  - deal with pubdub if run via cron!

  ## Broken links Ive found:
  ```Both of these:
      --- Entry 1 (MEDIA from media_data.csv) ---
      title               : A global index insurance design for agriculture
      external_link       : http://agfax.com/2018/09/04/a-global-index-insurance-design-for-agriculture/
      date                : 2018-09-04
      source              : agfax.com
    
      --- Entry 2 (MEDIA from media_data.csv) ---
      title               : A global index insurance design for agriculture
      external_link       : https://www.engineering.columbia.edu/news/global-index-insurance-design-agriculture
      date                : 2018-08-20
      source              : engineering.columbia.edu'''

  
      
