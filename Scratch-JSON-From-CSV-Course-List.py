import requests, json, time
from datetime import datetime
import pandas as pd

#Assign or create a file directory for JSON files
courses_dir = r'C:\tmp\alma\courses'
csv_filepath = "YOUR CSV FILEPATH"

# Open csv file listing representations
d = pd.read_csv(csv_filepath, dtype=str)
d.set_index("course_code", inplace=True, drop=True)

# API key
api_key = "YOUR API KEY"

# Collect course data from the CSV file
def GetCourseData(index, row):
    course_code = index
    course_name = row['course_name']
    course_section = row['course_section']
    course_dept = row['course_dept']
    course_term = row['course_term']
    course_start_date = row['course_start_date']
    course_end_date =  row['course_end_date']
    course_year = row['course_year']
    course_instructor_id = row['course_instructor_id']
    searchable_id = row['searchable_id']

    course_data = [course_code,
                   course_name,
                   course_section,
                   course_dept,
                   course_term,
                   course_start_date,
                   course_end_date,
                   course_year,
                   course_instructor_id,
                   searchable_id]

    # Construct a dictionary to contain all the course data so it can be dumped to a JSON file
    course_dict = {
        'code' : course_code,
        'name' : course_name,
        'section' : course_section,
        'academic_department' : {'value' : course_dept},
        'processing_department' : {'value' : "Main",
                                   'desc' : 'Main Galvin Reserve'},
        'term' : [{'value' : course_term}],
        'status' : "INACTIVE",
        'start_date' : str(course_start_date + 'Z'),
        'end_date' : str(course_end_date + 'Z'),
        'year' : course_year,
        'instructor' : [{'primary_id' : course_instructor_id}],
        'searchable_id' : [searchable_id]
    }
    return course_dict

def CreateCourse(course_dict, api_key):
    apicall = 'https://api-na.hosted.exlibrisgroup.com/almaws/v1/courses?{format}&apikey={api_key}'
    format = "format=json"
    headers = {
        "Authorization": f"apikey {api_key}",
        "Content-Type": "application/json"
    }
    response = requests.get(apicall.format(format=format, api_key=api_key))


    if response.status_code == 200:
        # API call successful
        add_course = requests.post(apicall.format(format=format, api_key=api_key), headers=headers,
                                   data=json.dumps(course_dict))
        if add_course.status_code == 200:
            add_course_json = add_course.json()
            print(add_course_json)
            course_id = add_course_json['id']
            time.sleep(2)
            new_apicall = 'https://api-na.hosted.exlibrisgroup.com/almaws/v1/courses?{format}&apikey={api_key}&q=course_id~{course_id}'
            response2 = requests.get(new_apicall.format(format=format, api_key=api_key, course_id=course_id))
            new_course_data = response2.json()
            time.sleep(2)
            print("Check Call: " + str(new_course_data))
            return course_id

        else:
            #API call failed
            course_exist = "course exists"
            return course_exist

def CreateReadingList(course_id, api_key):
    apicall = 'https://api-na.hosted.exlibrisgroup.com/almaws/v1/courses/{course_id}?{format}&apikey={api_key}'
    format = "format=json"
    headers = {
        "Authorization": f"apikey {api_key}",
        "Content-Type": "application/json"
    }
    response = requests.get(apicall.format(course_id=course_id, format=format, api_key=api_key))

    if response.status_code == 200:
        course_data = response.json()

        # Set up data dictionary for the new reading list
        list_code_draft = str(course_data['code'] + "-" + str(course_data['section']) + "-" + course_data['instructor'][0]['last_name'])
        list_code = list_code_draft.replace(" ", "-")

        reading_list_dict = {
            'code' : list_code,
            'name' : str(course_data['name']),
            'due_back_date' : str(course_data['end_date']),
            'status' : {'value' : 'Complete'},
            'visibility' : {'value' : 'OPEN_TO_WORLD'},
            'publishingStatus' : {'value' : 'DRAFT'}
        }

        # Push data dictionary to Alma as a JSON
        list_apicall = 'https://api-na.hosted.exlibrisgroup.com/almaws/v1/courses/{course_id}/reading-lists?{format}&apikey={api_key}'
        list_post = requests.post(list_apicall.format(course_id=course_id, format=format, api_key=api_key), data=json.dumps(reading_list_dict),headers=headers)
        print(list_post.json())
        time.sleep(2)

        if list_post.status_code == 200:
            check_list_call = 'https://api-na.hosted.exlibrisgroup.com/almaws/v1/courses/{course_id}/reading-lists?{format}&apikey={api_key}&q=code~{list_code}'
            check_list = requests.get(check_list_call.format(course_id=course_id, format=format, api_key=api_key, list_code=list_code))
            new_list_data = check_list.json()
            confirmed_list_code = new_list_data['reading_list'][0]['code']

            course_data['reading_lists'] = new_list_data
            associate_list = requests.put(apicall.format(course_id=course_id,format = format, api_key=api_key), headers=headers, data=json.dumps(course_data))
            print(associate_list.json())
            return confirmed_list_code

        else:
            # Check API Call Failed
            list_error = 'No Reading List Found'
            return list_error

# API call successful

for index, row in d.iterrows():
    course_dict = GetCourseData(index, row)
    print(course_dict)

    # Dump JSON to file
    now = datetime.now()
    filename = str(index + "-" + now.strftime('%d-%m-%y-%H-%M-%S'))
    file = open(courses_dir + "\\" + str(filename) + ".json", 'a', encoding='utf-8')
    file.writelines(json.dumps(course_dict))

    # Push course data to Alma
    course_id = CreateCourse(course_dict, api_key)

    if course_id == "course exists":
        print(course_dict['code'] + " already exists. Alma was not updated. Moving to the next course.")
        pass

    else:

        # Update the CSV with the new Course ID
        d.loc[index, 'course_id'] = course_id
        d = d.astype(str)

        # Update the CSV with the new Reading List Code
        reading_list_id = CreateReadingList(course_id, api_key)
        d.loc[index, 'list_code'] = reading_list_id
        d.to_csv(csv_filepath)

## A function to read a course JSON and push it to Alma to create a new course can then be created,
## with error handling in case the course already exists somehow.

## A next step could be to include reading list and citation data in the CSV so reading lists
## can be automatically added and citations can be associated with them.
