# This is a repo for FI list of links based on csv file: https://ccsfist.github.io/filist/

### To update the filist

### Immediate next steps:
   - need to add features to include new pubs, look for duplicates across merged csv file, keep image cache working with new documents
   - forcerank column in csv file that allows you to have items sit near the top of the html, irregardless of the date
   - check for broken links (perhaps keeping them in the list as a kind of cv, but not active)
   - cache as much as possible from the IRI data library and other less permanent sources, perhaps not to this repo/html, but somewhere!

   - add any images to the images directory in the repo
   - edit combined_data.csv file to generate all the entries
       - Note its format was the combination of 3 spreadsheets by ai so it doesnt make complete sense (someday, hopefully).  
       - Depending on the kind of entry, you need to put the information (like titles, urls, etc) in different parts of the spreadsheet
       - It has redundant columns, where different columns only work for different kinds of entries
   - you run python make_simplefihtml.py and it generates index.html
   - double check that index.html looks ok
   - git add, commit, and push

### It came from DOsgoodCU/filinks
  - That repo had a lot of conversion from old sources steps
    - started with the old https://iri.columbia.edu/topics/financial-instruments/
    - added things listed as author Daniel Osgood in columbia commons
    - used 3 csv files supplied by Jeff Turmelle (related to the IRI website generation)
    - cached images for news/pub items from the old iri website and other sources(partially manually)
    - had a python script that generated an index.html file
  - Once that was set up (multifile subdirectory now), scripts were made to make it simpler for future use (singlefile folder of repo is starting point)


### Important functionality to develop
  - test for broken links
  - make more general script to query Academic Commons once they update their API
  - make duplicate link detector (some early attempts for single csv file in filinks)
    -this will be important for when academic commons script is done, as we will want journals to be linked to when there are links to both academic commons and also to journals

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

  
      
