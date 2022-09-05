from django.conf import settings
from python_ags4 import AGS4

dicts_path = settings.MEDIA_ROOT + '\\ags\\dicts'

ags_dics = {
"AGS403":"Standard_dictionary_v4_0_3.ags",
"AGS404":"Standard_dictionary_v4_0_4.ags",
"AGS41" :"Standard_dictionary_v4_1.ags",
"AGS411" :"Standard_dictionary_v4_1_1.ags"
}

title = "AECOM Ground Engineering"
header = "AGS File Checker"

version = "Beta v0.0.1"
release_date = "2022-09-05"

def check_file (input_file, version):
    
    dict_file = ags_dics[version]
    
    if dict_file:
        return print_to_string(AGS4.check_file(input_file, "{0}\\{1}".format (dicts_path, dict_file)))
    
    return "AGS version ({0}) dictionary not found".format(version)

def export_xlsx(input_file, output_file):
    AGS4.AGS4_to_excel(input_file, output_file)

def print_to_string(ags_errors):
    return '\n'.join(print_to_array(ags_errors))

def print_to_array(ags_errors):

    '''Print error report to array.'''
    arr =  []
    
    arr.append (title)
    arr.append (header + ' ' + version + " (" + release_date + ")")
    arr.append ('')

    error_count = 0
    for key, val in ags_errors.items():
        if 'Rule' in key:
            error_count += len(val)

    # Print  metadata
    if 'Metadata' in ags_errors.keys():
        for entry in ags_errors['Metadata']:
            arr.append(f'''{entry['line']}: \t {entry['desc']}''')
        arr.append('')

    # Summary of errors log
    if error_count == 0:
        arr.append('All checks passed.\n')
    else:
        arr.append(f'{error_count} error(s) found in file.\n')

    # Print 'General' error messages first if present
    if 'General' in ags_errors.keys():
        arr.append('General:')

        for entry in ags_errors['General']:
            arr.append(f'''  {entry['desc']}''')
        arr.append('')

    # Print other error messages
    for key in [x for x in ags_errors if 'Rule' in x]:
        arr.append("FAIL: "f'''{key}:''')
        for entry in ags_errors[key]:
            arr.append(f'''  Line {entry['line']}\t {entry['group'].strip('"')}\t {entry['desc']}''')
        arr.append('')
    
    return arr;
   