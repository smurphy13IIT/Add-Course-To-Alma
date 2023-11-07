import pandas as pd

#The citations file comes directly from the IIT Bookstore
citations_filepath = "citations.csv"

#The mmsid file is the output of an Alma Analytics report filtered to the ISBNs of this semester's reserves
mmsid_filepath = "mmsid.csv"

current_term = ["FALL", "2023", "2023-08-24", "2023-12-31"]

dcite = pd.read_csv(citations_filepath, dtype=str)
dcite.set_index("ID", inplace=True, drop=True)
dcite["MMSID"] = None
dcite["Semester"] = None
dcite["course_code"] = None

dmmsid = pd.read_csv(mmsid_filepath, dtype=str)
dmmsid.set_index("ISBN", inplace=True, drop=True)

mmsid_dict = {}


for index, row in dmmsid.iterrows():
    raw_isbns = index
    mmsid = row["MMS Id"]
    isbns = raw_isbns.split("; ")
    for i in isbns:
     mmsid_dict[i] = mmsid

for index, row in dcite.iterrows():
    #Format the list of citations properly so the Course Updater can understand it
    #Start by constructing a searchable course code for each citation
    raw_course_number = row['Dept/Course']
    raw_section = row['Section']
    current_semester = current_term[0] + str(current_term[1])
    
    #Create a column for the current semester
    dcite.loc[index, 'Semester'] = current_semester
    course_code = raw_course_number.replace(' ','') + "-0" + str(raw_section) + current_semester
    
    #Create a column for the new course codes
    dcite.loc[index, 'course_code'] = course_code
    print(course_code)

    #Remove dashes from the ISBN number and update the CSV
    raw_isbn = row["ISBN"]
    isbn = raw_isbn.replace('-', '')
    dcite.loc[index, 'ISBN'] = isbn

    #Match ISBN numbers to the MMSID list retrieved from Alma Analytics
    #Create a column for MMSIDs
    if isbn in mmsid_dict:
        dcite.loc[index, 'MMSID'] = mmsid_dict[isbn]
        print(row['Title'] + ": MMSID Found")

dcite.to_csv(citations_filepath)


