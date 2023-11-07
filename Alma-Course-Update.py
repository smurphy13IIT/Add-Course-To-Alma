import requests, json, time, os
from datetime import datetime
from dictionaries import codes_dict, month_dict
from citations_cleanup import current_term
import pandas as pd

# TO DO:
# Add code to the AddCitation function to prevent duplicate citations


#Assign or create a file directory for JSON files
courses_dir = r'C:\tmp\alma\courses'
courses_filepath = "courses.csv"
citations_filepath = "citations.csv"

# Open csv files listing course information, retrieved from https://wildfly-prd.iit.edu/coursestatusreport/
d = pd.read_csv(courses_filepath, dtype=str)
d.set_index("CRN", inplace=True, drop=True)
d["course_id"] = None
d["list_code"] = None

dcite = pd.read_csv(citations_filepath, dtype=str)
dcite.set_index("ID", inplace=True, drop=True)
dcite['Status'] = None

# API key
api_key = "YOUR API KEY HERE"

# Collect course data from the CSV file
def GetCourseData(api_key, current_term, index, row):
    course_CRN = index
    course_code = row['Course Code']
    course_name = row['Course Title']
    course_number, course_section = course_code.split("-")
    course_dept = codes_dict[row['Course Subject']]
    course_term = current_term[0]

    # Start and end dates need to be properly formatted for Alma to understand them.
    try:
        raw_start_date, raw_end_date = row['Dates'].split(" to ")
        start_day, start_month, start_year = raw_start_date.split("-")
        course_start_date = "20" + str(start_year) + "-" + str(month_dict[start_month]) + "-" + str(start_day)
        end_day, end_month, end_year = raw_end_date.split("-")
        course_end_date = "20" + str(end_year) + "-" + str(month_dict[end_month]) + "-" + str(end_day)
    except:
        course_start_date = current_term[2]
        course_end_date = current_term[3]

    course_year = current_term[1]

    #The course CSV file contains only faculty names, but Alma needs primary identifiers.
    #The following lines of code will make an API call to retrieve the primary ID of the instructor.
    raw_name = row["Primary Instructor"]

    try:
        first_name, last_name = raw_name.split(", ")
        #Make an API call to search for the instructor name and retrieve a Primary ID.
        apicall = 'https://api-na.hosted.exlibrisgroup.com/almaws/v1/users?{format}&apikey={api_key}&q=ALL~{first_name}%2b{last_name}'
        format = "format=json"
        call_elements = {"format": format,
                         "api_key": api_key,
                         "first_name": first_name,
                         "last_name": last_name}

        response = requests.get(apicall.format(**call_elements))

        instr_response = response.json()
        course_instructor_id = ""

        if instr_response["total_record_count"] > 1:
            for i in instr_response["user"]:
                primary_id = i["primary_id"]
                inst_apicall = 'https://api-na.hosted.exlibrisgroup.com/almaws/v1/users/{primary_id}?{format}&apikey={api_key}'
                inst_call_elements = {"format": format,
                                      "api_key": api_key,
                                      "primary_id": primary_id}
                is_empl_response = requests.get(inst_apicall.format(**inst_call_elements))
                user_group = is_empl_response.json()["user_group"]["desc"]

                if user_group == "Academic Employees":
                    course_instructor_id = primary_id

        else:
            course_instructor_id = instr_response["user"][0]["primary_id"]

    except:
        course_instructor_id = ""

    semester = str(course_term + course_year)
    searchable_id = str(course_code.replace(" ", "") + str(semester))

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
        'status' : "ACTIVE",
        'start_date' : str(course_start_date + 'Z'),
        'end_date' : str(course_end_date + 'Z'),
        'year' : course_year,
        'instructor' : [{'primary_id' : course_instructor_id}],
        'searchable_id' : [searchable_id, course_number]
    }
    print(course_dict['code'] + " course data compiled.")
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
            print(str(course_dict['code']) + " Successfully Added")
            add_course_json = add_course.json()
            course_id = add_course_json['id']
            time.sleep(2)
            new_apicall = 'https://api-na.hosted.exlibrisgroup.com/almaws/v1/courses/{course_id}?{format}&apikey={api_key}'
            response2 = requests.get(new_apicall.format( course_id=course_id, format=format, api_key=api_key))
            new_course_data = response2.json()
            return course_id

        else:
            #Add course failed; the course may already exist. Try updating the existing course information.
            try:
                search_id = course_dict['searchable_id'][0]
                get_id_call = 'https://api-na.hosted.exlibrisgroup.com/almaws/v1/courses/?{format}&apikey={api_key}&q=searchable_ids~{search_id}'
                course_update_get = requests.get(get_id_call.format(format=format, api_key=api_key, search_id=search_id))
                course_id = course_update_get.json()['course'][0]['id']
                update_call = 'https://api-na.hosted.exlibrisgroup.com/almaws/v1/courses/{course_id}?{format}&apikey={api_key}'
                update_course = requests.put(update_call.format(course_id=course_id, format=format, api_key=api_key), headers=headers,
                                           data=json.dumps(course_dict))
                course_id = update_course.json()['id']
                print(str(course_dict['code']) + " Already Existed; Successfully Updated")
                return course_id

            #if that doesn't work, move on to the next course.
            except:
                course_add_error = "COURSE NOT ADDED/UPDATED"
                print(course_add_error)
                return course_add_error
    else:
        #API console is down
        api_down = "Alma API is down"
        print(api_down)
        quit()


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
        try:
            list_code_draft = str(course_data['code'] + "-" + str(course_data['section']) + "-" + course_data['instructor'][0]['last_name'])
            list_code = list_code_draft.replace(" ", "-")

        except:
            list_code_draft = str(course_data['code'] + "-" + str(course_data['section']) + "-" + "UnknownInstructor")
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
        time.sleep(2)

        if list_post.status_code == 200:
            check_list_call = 'https://api-na.hosted.exlibrisgroup.com/almaws/v1/courses/{course_id}/reading-lists?{format}&apikey={api_key}&q=code~{list_code}'
            check_list = requests.get(check_list_call.format(course_id=course_id, format=format, api_key=api_key, list_code=list_code))
            new_list_data = check_list.json()
            confirmed_list_code = new_list_data['reading_list'][0]['code']
            course_data['reading_lists'] = new_list_data

            associate_list = requests.put(apicall.format(course_id=course_id,format = format, api_key=api_key), headers=headers, data=json.dumps(course_data))

            if associate_list.status_code == 200:
                print(str("Reading List " + confirmed_list_code + " Created"))
                return confirmed_list_code

            else:
                print(str(confirmed_list_code + " created, but course association Failed"))
                pass

        else:

            get_existing_list_call = 'https://api-na.hosted.exlibrisgroup.com/almaws/v1/courses/{course_id}/reading-lists?{format}&apikey={api_key}&q=code~{list_code}'
            get_existing_list = requests.get(get_existing_list_call.format(course_id=course_id, format=format,api_key=api_key,list_code=list_code))
            existing_list_data = get_existing_list.json()
            existing_list_id = existing_list_data['reading_list'][0]['id']

            update_list_call = 'https://api-na.hosted.exlibrisgroup.com/almaws/v1/courses/{course_id}/reading-lists/{list_id}?{format}&apikey={api_key}'
            list_delete = requests.delete(update_list_call.format(course_id=course_id, list_id=existing_list_id, format=format, api_key=api_key), headers=headers)

            update_list = requests.post(list_apicall.format(course_id=course_id, format=format, api_key=api_key), data=json.dumps(reading_list_dict), headers=headers)
            print("Existing list updated: " + str(update_list.json()['code']))
            updated_list_code = update_list.json()['code']
            return updated_list_code

    else:
        # Check API Call Failed
        list_error = 'No Course Found - List Not Created'
        print(list_error)
        pass

    print("\n")


# This function should be run after all courses and reading lists have either been
# created or updated. Use a "For" loop to iterate over a CSV of citations and associate
# each one with the appropriate course and reading list.
def AddCitation(index, row, api_key):

    format = "format=json"
    headers = {
        "Authorization": f"apikey {api_key}",
        "Content-Type": "application/json"
    }

    course_code = index
    mms_id = str(row['MMSID'])
    search_id = row['course_code']

    # Construct a dictionary for the citation that can be pushed to Alma as JSON
    citation_dict = {
        'status' : {'value': 'Complete'},
        "copyrights_status": {
            "value": "NOTDETERMINED"
        },
        'metadata' : {
            'mms_id' : mms_id
        },
        'type' : {
            'value' : 'BK',
            'desc' : 'Physical Book'
        }
        }

    course_call = 'https://api-na.hosted.exlibrisgroup.com/almaws/v1/courses?{format}&apikey={api_key}&q=searchable_ids~{search_id}'
    get_course_data = requests.get(course_call.format(format=format, api_key=api_key, search_id=search_id))
    course_data = get_course_data.json()
    try:
        course_id = str(course_data['course'][0]['id'])

    except:
        return("Course Not Found for Citation")


    course_lists_call = 'https://api-na.hosted.exlibrisgroup.com/almaws/v1/courses/{course_id}/reading-lists?{format}&apikey={api_key}'
    get_list_id = requests.get(course_lists_call.format(course_id=course_id, format=format, api_key=api_key))
    list_data = get_list_id.json()
    list_id = str(list_data['reading_list'][0]['id'])

    list_call = 'https://api-na.hosted.exlibrisgroup.com/almaws/v1/courses/{course_id}/reading-lists/{list_id}/citations?{format}&apikey={api_key}'
    post_citation = requests.post(list_call.format(course_id=course_id, list_id=list_id, format=format, api_key=api_key), headers=headers, data=json.dumps(citation_dict))

    if post_citation.status_code == 200:
        row['status'] = 'Posted'
        return str(course_code + " citation successfully posted")

    else:
        row['status'] = 'Not Posted'
        return str(course_code + " citation not posted")


# Main Loop
for index, row in d.iterrows():
    if (row['Campus'] == 'Mies' or row['Campus'] == 'Internet') and row['Course Subject'] != "ARCH":

        course_dict = GetCourseData(api_key, current_term, index, row)
        # Dump JSON to file
        now = datetime.now()
        filename = str(index + "-" + now.strftime('%d-%m-%y-%H-%M-%S'))
        file = open(courses_dir + "\\" + str(filename) + ".json", 'a', encoding='utf-8')
        file.writelines(json.dumps(course_dict))

        # Push course data to Alma
        course_id = CreateCourse(course_dict, api_key)

        # Update the CSV with the new Course ID
        d.loc[index, 'course_id'] = course_id

        # Update the CSV with the new Reading List Code
        reading_list_id = CreateReadingList(course_id, api_key)
        d.loc[index, 'list_code'] = reading_list_id
        d.to_csv(courses_filepath)

for index, row in dcite.iterrows():
    add_citation = AddCitation(index, row, api_key)
    dcite.loc[index, 'Status'] = add_citation
    d.to_csv(citations_filepath)
    print(add_citation)

print("Course Update Process Completed.")
