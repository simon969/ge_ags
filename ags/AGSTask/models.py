import os
import uuid
import json
from datetime import datetime
import pytz
from django.db import models
from django.db.models import Q
from ags.pyAGS.AGSProcessing import processAGS
from django.core.files.base import ContentFile
from ge_py.quickstart.models import is_null_or_empty
from ags.pyAGS.AGSWorkingGroup import check_file
from ags.pyAGS.AGSWorkingGroup import export_xlsx

DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S' 

# Create your models here.
class Status:
        FAIL = -1
        READY = 0
        PROCESSING = 1
        SUCCESS = 2
def task_doc_path (instance, filename):
    return 'ags/documents/{0}/{1}'.format(str(instance.task.id), filename)

class AGSTask (models.Model):
    id = models.UUIDField(
         primary_key = True,
         default = uuid.uuid4,
         editable = False)
    task = models.JSONField(blank=False, default=dict)
    files = models.TextField(blank=True)
    result = models.TextField(blank=True)
    createdDT = models.DateTimeField(auto_now_add=True)
    completedDT = models.DateTimeField(null=True, blank=True)
    progress = models.TextField(blank=True)
    status = models.IntegerField(null=False, default = 0)
    owner =  models.CharField(max_length=100, blank=False)
    class Meta:
     ordering = ['createdDT']
    def progress_add (self, msg):
        self.progress += "{0}  {1}".format(datetime.now().strftime(DATETIME_FORMAT), msg + '\n')

class AGSDocuments (models.Model):
    id = models.UUIDField(
         primary_key = True,
         default = uuid.uuid4,
         editable = False)
    task = models.ForeignKey(AGSTask, related_name="taskfiles", on_delete=models.CASCADE) #NOQA
    document = models.FileField (upload_to=task_doc_path, null=True,blank=True)
    ## document = models.FileField (upload_to='ags/documents/%Y/%m/%d',null=True, blank=True)

def get_task_files (pk):
     
     """
     return a comma separated list of filenames associated with this task id
     """
     
     task_docs = AGSDocuments.objects.filter(Q(task_id=pk))
     if task_docs is None:
               return
     files = []
     for doc in task_docs:
          files.append(os.path.basename(doc.document.name))
     return  ",".join(files)

def get_task_results(pk, override=False):

     """
     retrieve the ags task, run it and save results

     """

     try:
          task = AGSTask.objects.get(pk=pk) 
          ags_docs = AGSDocuments.objects.filter(Q(document__contains='.ags'), Q(task_id=pk))
          if task is None or ags_docs is None:
               return
     except Exception as e:
          print (getattr(e, 'message', repr(e)))
          return
     
     if (task.status == Status.PROCESSING and override==False):
          return

     task.progress_add ("get_task_results() started")
     task.status = Status.PROCESSING
     task.save()
     
     try:
          if (task.task):
               task_info = json.loads(task.task.replace("'","\""))
          
               paths = []
               for doc in ags_docs:
                    paths.append(doc.document.path)
               
               if 'processAGS' in task_info['actions'] and len(paths) > 0 :
                   
                    if 'ags_summary' in task_info['results']:
                         ap = processAGS (paths)
                         ap.process()
                         result = ap.report_summary ()
                         csv_file = "ags_summary.csv"
                         content = ContentFile (content=result, name=csv_file )
                         file = AGSDocuments.objects.create(task=task, document=content)
                         file.save() 
                         task.progress_add('report summary created:' + csv_file)
                         task.save()
                    
                         if 'ags_lines' in task_info['results']:
                              result = ap.report_lines ()
                              csv_file = "ags_lines.csv"
                              content = ContentFile (content=result, name=csv_file)
                              file = AGSDocuments.objects.create(task=task, document=content)
                              file.save() 
                              task.progress_add('report lines created:' + csv_file)
                              task.save()
                    
                    if 'export_xlsx' in task_info['results']:
                         for path in paths:
                              head, tail = os.path.split(path)
                              xlsx_file = tail.replace('.ags','.xlsx') 
                              content = ContentFile (content='empty', name=xlsx_file)
                              file = AGSDocuments.objects.create(task=task, document=content)
                              file.save() 
                              xls_path = path.replace('.ags','.xlsx') 
                              export_xlsx (path, xls_path)
                              task.progress_add('excel exported:' + xlsx_file)
                              task.save()

                    if 'check' in task_info['results']:
                         for path in paths:
                              version = task_info['version']
                              result = check_file(path,version)
                              head, tail = os.path.split(path)
                              txt_file = tail.replace('.ags',' check.txt')
                              content = ContentFile (content=result, name=txt_file )
                              file = AGSDocuments.objects.create(task=task, document=content)
                              file.save() 
                              task.progress_add('check report:' + txt_file)
                              task.save()
               
               task.files =  get_task_files(task.id)
               task.completedDT = datetime.now(pytz.UTC)
               task.progress_add ("get_task_results() completed")
               task.status = Status.SUCCESS
               task.save()
          
              
     except Exception as e:
          print (getattr(e, 'message', repr(e)))
          task.progress_add(getattr(e, 'message', repr(e)))
          task.status = Status.FAIL
          task.save()
           
    