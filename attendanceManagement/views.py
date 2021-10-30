from django.shortcuts import render,redirect
from django.http import JsonResponse
from authentication.views import checkAuth
from CollegeManagement.OtherFunction import ManageProject
from CollegeManagement.settings import BASE_DIR
import threading
from . import attendanceModal
import pandas as pd
from CollegeManagement.connection import createDataConnection
from functools import reduce
from dateutil.parser import parse
import datetime
def uploadAttendencePage(request,token):
    try:
        ip = request.META['REMOTE_ADDR']
        res = checkAuth(token, ip)
        if (res[0]):
            return render(request,"uploadAttendence.html",{"token":token})
        else:
            if (res[1] == 0):
                return redirect("/authentication/login")
            elif (res[1] == -1):
                return JsonResponse({"msg": "Invalid Authentication"}, status=401)
            else:
                return JsonResponse({"status": False})
    except Exception as e:
        print(e)
        return JsonResponse({"data":{}})

def uploadAttendenceFileUrl(request,token):
    try:
        ip = request.META['REMOTE_ADDR']
        res = checkAuth(token, ip)
        if (res[0]):
            data = request.POST
            subjectid=data['subjectid']
            file = request.FILES['attendencefile']
            date=data['dateupload']
            date=datetime.date.fromisoformat(date).toordinal()
            fileid=ManageProject.fileUniqueId(file=file)
            res=uploadAttenceFile(file,fileid)
            if(res[0]):
                res=res[1]
                manageAttendence=threading.Thread(target=analysis,args=(res[2],subjectid,fileid,date))
                manageAttendence.start()
                res=attendanceModal.uploadAttendenceFile(fileid,subjectid,res[1],date)
                if(res):
                    return JsonResponse({"status": True})
                else:
                    return JsonResponse({"status": False})
            else:
                return JsonResponse({"status": False})
        else:
            if (res[1] == 0):
                return redirect("/authentication/login")
            elif (res[1] == -1):
                return JsonResponse({"msg": "Invalid Authentication"}, status=401)
            else:
                return JsonResponse({"status": False})
    except Exception as e:
        print(e)
        return JsonResponse({"status": False})

def uploadAttenceFile(file,id):
    try:
        f=open(f"{BASE_DIR}/publicFiles/userUploadedFiles/attendenceFiles/{id}",'wb')
        for chunk in file.chunks():
            f.write(chunk)
        f.close()
        p=manageCSV(f"{BASE_DIR}/publicFiles/userUploadedFiles/attendenceFiles/{id}")
        if(p[0]):
            return True,p
        else:
            return [False]
    except Exception as e:
        print(e)
        return False,0

def manageCSV(file):
    f=open(file,"r")
    data=f.read()[2:].replace("\x00","")
    f.close()
    data=data.strip()
    f=open(file,"w")
    f.write(data)
    f.close()
    p=convertToFrame(file)
    return p

def Computation(a,b):
    sec1=a.second
    sec2=b.second
    min1=a.minute
    min2=b.minute
    hour1=a.hour
    hour2=b.hour
    if(sec1>sec2):
        min2-=1
        sec=60+sec2-sec1
    else:
        sec=sec2-sec1
    if (min1 > min2):
        hour2 -= 1
        min = 60 + min2 - min1
    else:
        min = min2 - min1
    hour=hour2-hour1
    return a.replace(hour,min,sec)
def Computation1(a,b):
    sec=abs(a.second+b.second)
    min=abs(a.minute+b.minute+sec//60)
    sec=sec%60
    hour=abs(a.hour+b.hour+min//60)
    min=min%60
    return a.replace(hour,min,sec)
def manageTimeStamp(name,data):
    left = (data[(data["Full Name"] == name) & (data["User Action"] == "Left")]["Timestamp"])
    join = (data[(data["Full Name"] == name) & (data["User Action"] == "Joined")]["Timestamp"])
    if (len(left) != len(join)):
        left = list(left)
        left.append(parse(f"{12}:{00}:{00}").timetz())
    data = map(Computation, join, left)
    data = list(data)
    data = reduce(Computation1, data)
    return data
def convertToFrame(file):
    try:
        data = pd.read_csv(file, sep="\t")
        return True,len(set(data['Full Name']))-1,data
    except Exception as e:
        print(e)
        return [False]
def analysis(data,subjectid,file,date):
    try:
        data['Timestamp'] = [parse(data['Timestamp'][i]).timetz() for i in range(0, len(data["Timestamp"]))]
        names=set(data["Full Name"])
        res=attendanceModal.fetchAllStudent(subjectid)
        data1= pd.DataFrame({"studentid":[item['studentid'] for item in res[1]],"name":[item['name'] for item in res[1]]})
        data1[['time',f"{datetime.date.fromordinal(date)}"]]=[[manageTimeStamp(name, data),"P"] if(name in names) else [0,"A"] for name in data1['name']]
        data1['subjectid']=subjectid
        data1.to_csv(f"{BASE_DIR}/publicFiles/userUploadedFiles/attendenceFiles/{file}",index=False)
        data1['date']=str(date)
        engine=createDataConnection()
        data1=data1.rename({f"{datetime.date.fromordinal(date)}":"attendence"},axis="columns")
        data1[['studentid',"subjectid","date","attendence"]].to_sql('studentattendence', con=engine, if_exists="append", index=False)
    except Exception as e:
        print(e)
def getAttendence(request,token):
    try:
        ip = request.META['REMOTE_ADDR']
        res = checkAuth(token, ip)
        if (res[0]):
            date=request.GET['date']
            id=request.GET['subjectid']
            date=datetime.date.fromisoformat(date).toordinal()
            data=attendanceModal.getAttendence(id,date)
            if(data[0]):
                data[2] = list(zip(*data[2]))
                data[2] = dict(zip(["Student Id", "Name", "Present", "Absent"], data[2]))
                generateAnalysisFile(data[2],data[1]['filename'])
                return JsonResponse({"data":data[1],"analysis":data[2]})
            else:
                return JsonResponse({"data":{}})
        else:
            if (res[1] == 0):
                return redirect("/authentication/login")
            elif (res[1] == -1):
                return JsonResponse({"msg": "Invalid Authentication"}, status=401)
            else:
                return JsonResponse({"status": False})
    except Exception as e:
        print(e)
        return JsonResponse({"data":{}})
def generateAnalysisFile(res,filename):
    try:
        res=pd.DataFrame(res)
        res['Total Days']=res['Present']+res['Absent']
        res['Percentage']=res['Present']*100/res["Total Days"]
        res.to_csv(f"{BASE_DIR}/publicFiles/userUploadedFiles/attendenceFiles/analysis{filename}",index=False)
    except Exception as e:
        print(e)

