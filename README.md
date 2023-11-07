# Add-Course-To-Alma

This program takes course and textbook data and formats it so that course and citation data are updated in Alma.
This process should occur before the start of each semester. Because the functions in the script check to see whether courses, reading lists, and citations already exist in Alma before creating new ones, you can run this program as many times as you need to as new textbook information comes in from faculty or from the bookstore. Simply update the **citations.csv** file with the new data.


**Steps for Running This Program to Update Course and Citation Data in Alma:**

1. Gather the required data files
   
  a. An export of all courses for the semester from https://wildfly-prd.iit.edu/coursestatusreport/
  b. A file containing all textbooks needed for reserves this semester; this comes from the University Bookstore and may require some cleanup to remove non-textbook items and books for graduate courses

2. Download all files in this repository to the same folder. Update **Alma-Course-Update.py** with your own API key (the api_key variable in line 27), and update **citations_cleanup.py** with the current semester information (the current_term variable in line 9).
   
3. Rename your course file "courses.csv" and your textbook file "citations.csv" to match the filenames from this repository.
   
4. Move them into the repository folder; replace the existing "courses.csv" and "citations.csv" files with your new files.
   
5. Run **citations_cleanup.py**. This will remove all the dashes from the ISBN numbers in the citations file so you can use them as search queries in Alma Analytics.
   
6. Go to Alma Analytics and create an analysis using the **Physical Items** subject area. Select **ISBN** and **MMSID** as search fields. Use a filter on the ISBN field to limit the analysis to only the list of ISBNs in the citations.csv file.
   
7. Save the output of this anaysis as **mmsid.csv** and put it in the repository folder, replacing the existing file with the same name.
    
8. Run **citations_cleanup.py** again. This will cross-reference the mmsid.csv data with the textbook data. Not every item in the textbook list will have an associated MMSID; they will only have a MMSID if a record for the item currently exists in Alma.
    
9. Run **Alma-Course-Update.py**. This will take a while depending on the number of courses in the **courses.csv** file. Here's what this script does, in a nutshell:
   a. First, it collects data from the courses file and compiles a dictionary for each course that aligns with the data structure that Alma accepts for creating a new course. A unique ID is created for each course that can be referenced to add citations later.
   b. Next, it creates the new course using the Alma API by pushing the compiled course data as a JSON file to the Alma server.
   c. A reading list for each course is then created using additional course information retrieved from Alma after each course is created.
   d. Each reading list is populated with citations using the unique course code created in step a. Citations are only added after all courses and reading lists have been created.
   
