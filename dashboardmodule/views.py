from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.hashers import make_password
from django.contrib import messages
from django.db.models import Count, Q
from django.http import (
    HttpResponseRedirect, HttpResponse)
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext, loader
from django.contrib.auth.models import User
from datetime import date, timedelta, datetime
# from django.utils import simplejson
import json
import logging
import sys
import operator
import pandas
from django.shortcuts import render
import numpy
import time
import datetime
from django.core.files.storage import FileSystemStorage

from django.core.urlresolvers import reverse


from django.db import (IntegrityError, transaction)
from django.db.models import ProtectedError
from django.shortcuts import redirect
from onadata.apps.main.models.user_profile import UserProfile
from onadata.apps.usermodule.forms import UserForm, UserProfileForm, ChangePasswordForm, UserEditForm, OrganizationForm, \
    OrganizationDataAccessForm, ResetPasswordForm
from onadata.apps.usermodule.models import UserModuleProfile, UserPasswordHistory, UserFailedLogin, Organizations, \
    OrganizationDataAccess

from django.contrib.auth.decorators import login_required, user_passes_test
from django import forms
# Menu imports
from onadata.apps.usermodule.forms import MenuForm
from onadata.apps.usermodule.models import MenuItem
# Unicef Imports
from onadata.apps.logger.models import Instance, XForm
# Organization Roles Import
from onadata.apps.usermodule.models import OrganizationRole, MenuRoleMap, UserRoleMap
from onadata.apps.usermodule.forms import OrganizationRoleForm, RoleMenuMapForm, UserRoleMapForm, UserRoleMapfForm
from django.forms.models import inlineformset_factory, modelformset_factory
from django.forms.formsets import formset_factory

from django.core.exceptions import ObjectDoesNotExist
from django.views.decorators.csrf import csrf_exempt
from django.db import connection
from collections import OrderedDict
import os
import urllib2


def __db_fetch_values(query):
    cursor = connection.cursor()
    cursor.execute(query)
    fetchVal = cursor.fetchall()
    cursor.close()
    return fetchVal


def __db_fetch_single_value(query):
    cursor = connection.cursor()
    cursor.execute(query)
    fetchVal = cursor.fetchone()
    cursor.close()
    return fetchVal[0]


def __db_fetch_values_dict(query):
    cursor = connection.cursor()
    cursor.execute(query)
    fetchVal = dictfetchall(cursor)
    cursor.close()
    return fetchVal


def __db_commit_query(query):
    cursor = connection.cursor()
    cursor.execute(query)
    connection.commit()
    cursor.close()


def dictfetchall(cursor):
    desc = cursor.description
    return [
        OrderedDict(zip([col[0] for col in desc], row))
        for row in cursor.fetchall()]


def decimal_date_default(obj):
    if isinstance(obj, decimal.Decimal):
        return float(obj)
    elif hasattr(obj, 'isoformat'):
        return obj.isoformat()
    else:
        return obj
    raise TypeError


def index(request):
    return render(request, 'dashboardmodule/index.html')

def daily_service_trend(request):
    # query for  bar chart
    query = "with t as( select distinct designationvisitor from data_info where designationvisitor !=''),t1 as( select distinct sdate from data_info ),t3 as( select * from t,t1 order by sdate ),t4 as ( select designationvisitor,sdate,count(*) total from data_info where designationvisitor !='' group by designationvisitor,sdate order by sdate ) select t3.designationvisitor,t3.sdate,coalesce(total,0) total from t3 left join t4 on t3.designationvisitor = t4.designationvisitor and t3.sdate = t4.sdate order by t3.sdate"
    df = pandas.DataFrame()
    df = pandas.read_sql(query, connection)
    categories = json.dumps(df['sdate'].unique().tolist(), default=decimal_date_default)
    print len(df['sdate'].unique().tolist())
    name = ["Farmer","Agro Bussiness","Agricultural Professionals and Local Leaders"]
    data = []
    for each in df['designationvisitor'].unique().tolist():
        data.append(df['total'][df['designationvisitor'] == each].tolist())

    query = "select designationvisitor,count(*) from data_info where designationvisitor !='' group by designationvisitor order by designationvisitor"
    df = pandas.DataFrame()
    df = pandas.read_sql(query, connection)
    data_json = json.loads(df.to_json(orient='records'))
    farmer_count = 0
    agro_count = 0
    agro_leader_count = 0
    if not df.empty:
        if len(data_json) > 0 and data_json[0]['designationvisitor'] == "1":
            farmer_count = data_json[0]['count']
        if len(data_json) > 1 and data_json[1]['designationvisitor'] == "2":
            agro_count = data_json[1]['count']
        if len(data_json) > 2 and data_json[2]['designationvisitor'] == "3":
            agro_leader_count = data_json[2]['count']


    query = "with t as( select gender,count(*) from data_info where gender !='' group by gender), t1 as ( select sum(count) from t ) select gender,round(count*100/sum)::int as count from t,t1"
    df = pandas.DataFrame()
    df = pandas.read_sql(query, connection)
    data_json = json.loads(df.to_json(orient='records'))
    male_count = 0
    female_count = 0
    if not df.empty:
        if len(data_json) > 0 and data_json[0]['gender'] == "1":
            male_count = data_json[0]['count']
        if len(data_json) > 1 and data_json[1]['gender'] == "2":
            female_count = data_json[1]['count']

    # query for division
    query = "select id,field_name from geo_info where loc_type = 1"
    df = pandas.DataFrame()
    df = pandas.read_sql(query, connection)
    div_id = df.id.tolist()
    div_name = df.field_name.tolist()
    division = zip(div_id, div_name)

    print(len(categories))
    return render(request, 'dashboardmodule/daily_service_trend.html',{'categories': categories, 'name': name, 'data': data
                                                                       ,'farmer_count':farmer_count,'agro_count':agro_count
                                                                       ,'agro_leader_count':agro_leader_count
                                                                       ,'male_count':male_count,'female_count':female_count
                                                                       ,'division':division})


def data_filter_DST(request):
    division = json.loads(request.POST.get('division'))
    district = json.loads(request.POST.get('district'))
    upazila = json.loads(request.POST.get('upazila'))
    union = json.loads(request.POST.get('union'))
    # block = json.loads(request.POST.get('block'))
    saoo_name = json.loads(request.POST.get('saoo_name'))
    startdate = request.POST.get('startdate')
    enddate = request.POST.get('enddate')

    # query for stack column chart
    query_filter = " and sdate BETWEEN '" + str(startdate) + "' and '" + str(enddate) +"'"
    if division[0] is not None and  division[0] !="":
        division = str(map(str, division))
        division = division.replace('[', '(').replace(']', ')')
        query_filter += " and division in "+str(division)
    if district[0] is not None and  district[0] !="" :
        district = str(map(str, district))
        district = district.replace('[', '(').replace(']', ')')
        query_filter += " and district in "+str(district)
    if upazila[0] is not None and  upazila[0] !="":
        print(len(upazila))
        upazila = str(map(str, upazila))
        upazila = upazila.replace('[', '(').replace(']', ')')
        query_filter += " and upazilla in "+str(upazila)
    if union[0] is not None and  union[0] !="" :
        union = str(map(str, union))
        union = union.replace('[', '(').replace(']', ')')
        query_filter += " and union_name in "+str(union)
    # if block[0] is not None and  block[0] !="" :
    #     block = str(map(str, block))
    #     block = block.replace('[', '(').replace(']', ')')
    #     query_filter += " and block_name in "+str(block)
    if saoo_name[0] is not None and  saoo_name[0] !="" :
        saoo_name = str(map(str, saoo_name))
        saoo_name = saoo_name.replace('[', '(').replace(']', ')')
        query_filter += " and sender_id in "+str(saoo_name)

    query = "with t as( select distinct designationvisitor from data_info where designationvisitor !='' "+str(query_filter)+" ),t1 as( select distinct sdate from data_info where designationvisitor !='' "+str(query_filter)+"),t3 as( select * from t,t1 order by sdate ),t4 as ( select designationvisitor,sdate,count(*) total from data_info where designationvisitor !='' group by designationvisitor,sdate order by sdate ) select t3.designationvisitor,t3.sdate,coalesce(total,0) total from t3 left join t4 on t3.designationvisitor = t4.designationvisitor and t3.sdate = t4.sdate order by t3.sdate"
    df = pandas.DataFrame()
    df = pandas.read_sql(query, connection)
    categories = json.dumps(df['sdate'].unique().tolist(), default=decimal_date_default)
    name = ["Farmer", "Agro Bussiness", "Agricultural Professionals and Local Leaders"]
    data = []
    for each in df['designationvisitor'].unique().tolist():
        data.append(df['total'][df['designationvisitor'] == each].tolist())


    # query for the counting
    query = "select designationvisitor,count(*) from data_info where designationvisitor !='' "+str(query_filter)+" group by designationvisitor order by designationvisitor"
    df = pandas.DataFrame()
    df = pandas.read_sql(query, connection)
    print(query)
    data_json = json.loads(df.to_json(orient='records'))
    farmer_count =0
    agro_count = 0
    agro_leader_count = 0
    if not df.empty:
        if len(data_json)>0 and data_json[0]['designationvisitor'] == "1":
            farmer_count = data_json[0]['count']
        if len(data_json)>1 and data_json[1]['designationvisitor'] == "2":
            agro_count = data_json[1]['count']
        if len(data_json)>2 and data_json[2]['designationvisitor'] == "3":
            agro_leader_count = data_json[2]['count']

    query = "with t as( select gender,count(*) from data_info where gender !='' "+str(query_filter)+" group by gender), t1 as ( select sum(count) from t ) select gender,round(count*100/sum)::int as count from t,t1"
    df = pandas.DataFrame()
    df = pandas.read_sql(query, connection)
    data_json = json.loads(df.to_json(orient='records'))
    male_count = 0
    female_count = 0
    if not df.empty:
        if len(data_json)>0 and data_json[0]['gender'] == "1":
            male_count = data_json[0]['count']
        if len(data_json)>1 and data_json[1]['gender'] == "2":
            female_count = data_json[1]['count']
    return HttpResponse(json.dumps({'categories': categories, 'name': name, 'data': data,'farmer_count':farmer_count,'agro_count':agro_count
                                                                       ,'agro_leader_count':agro_leader_count
                                                                       ,'male_count':male_count,'female_count':female_count}))


def daily_saoo_service_trend(request):
    # query for the 7 categories
    query = "with t as( select unnest(string_to_array(problemreletedinfo,' ')) id from data_info), t1 as( select id,count(id) each_total from t group by id ), t2 as( select sum(each_total) total from t1 ) select id,round((each_total/total)*10,2) as percentage from t1,t2"
    df = pandas.DataFrame()
    df = pandas.read_sql(query,connection)
    seperate_categories = {}
    for i in range(7):
        seperate_categories[i] = 0
    for index,row in df.iterrows():
        seperate_categories[row['id']] = row['percentage']


    # query for stack column chart
    query = "with t as( select cropsname,unnest(string_to_array(problemreletedinfo,' ')) operation_id from data_info),t1 as ( select cropsname,operation_id,count(operation_id) each_operation from t group by cropsname,operation_id ), t2 as (select sum(each_operation) total from t1 ), t3 as( select distinct cropsname::int from data_info where cropsname != '' ),ts as( select distinct operation_id from t ), tres as ( select cropsname,operation_id from t3,ts) , t4 as( select cropsname::int,operation_id,round((each_operation/total)*100,2) as percentage from t1,t2 order by operation_id,cropsname::int ) select tres.cropsname,tres.operation_id,coalesce(percentage,0) percentage from tres left join t4 on tres.cropsname = t4.cropsname and tres.operation_id = t4.operation_id order by operation_id"
    df = pandas.DataFrame()
    df = pandas.read_sql(query, connection)
    categories = json.dumps(df['cropsname'].unique().tolist(), default=decimal_date_default)
    data = []
    for each in df['operation_id'].unique().tolist():
        data.append(df['percentage'][df['operation_id'] == each].tolist())


    #query for division
    query = "select id,field_name from geo_info where loc_type = 1"
    df = pandas.DataFrame()
    df = pandas.read_sql(query,connection)
    div_id = df.id.tolist()
    div_name = df.field_name.tolist()
    division = zip(div_id,div_name)
    return render(request, 'dashboardmodule/daily_saoo_service_trend.html',
                  {'categories': categories, 'data': data,'division':division,'seperate_categories':json.dumps({'seperate_categories':seperate_categories})})




def data_filter(request):
    division = json.loads(request.POST.get('division'))
    district = json.loads(request.POST.get('district'))
    upazila = json.loads(request.POST.get('upazila'))
    union = json.loads(request.POST.get('union'))
    # block = json.loads(request.POST.get('block'))
    saoo_name = json.loads(request.POST.get('saoo_name'))
    startdate = request.POST.get('startdate')
    enddate = request.POST.get('enddate')

    # query for stack column chart
    query_filter = " where sdate BETWEEN '" + str(startdate) + "' and '" + str(enddate) +"'"
    if division[0] is not None and  division[0] !="":
        division = str(map(str, division))
        division = division.replace('[', '(').replace(']', ')')
        query_filter += " and division in "+str(division)
    if district[0] is not None and  district[0] !="" :
        district = str(map(str, district))
        district = district.replace('[', '(').replace(']', ')')
        query_filter += " and district in "+str(district)
    if upazila[0] is not None and  upazila[0] !="":
        print(len(upazila))
        upazila = str(map(str, upazila))
        upazila = upazila.replace('[', '(').replace(']', ')')
        query_filter += " and upazilla in "+str(upazila)
    if union[0] is not None and  union[0] !="" :
        union = str(map(str, union))
        union = union.replace('[', '(').replace(']', ')')
        query_filter += " and union_name in "+str(union)
    # if block[0] is not None and  block[0] !="" :
    #     block = str(map(str, block))
    #     block = block.replace('[', '(').replace(']', ')')
    #     query_filter += " and block_name in "+str(block)
    if saoo_name[0] is not None and  saoo_name[0] !="" :
        saoo_name = str(map(str, saoo_name))
        saoo_name = saoo_name.replace('[', '(').replace(']', ')')
        query_filter += " and sender_id in "+str(saoo_name)
    query = "with t as( select cropsname,unnest(string_to_array(problemreletedinfo,' ')) operation_id from data_info "+str(query_filter)+"),t1 as ( select cropsname,operation_id,count(operation_id) each_operation from t group by cropsname,operation_id ), t2 as (select sum(each_operation) total from t1 ), t3 as( select distinct cropsname::int from data_info where cropsname != '' ),ts as( select distinct operation_id from t ), tres as ( select cropsname,operation_id from t3,ts) , t4 as( select cropsname::int,operation_id,round((each_operation/total)*100,2) as percentage from t1,t2 order by operation_id,cropsname::int ) select tres.cropsname,tres.operation_id,coalesce(percentage,0) percentage from tres left join t4 on tres.cropsname = t4.cropsname and tres.operation_id = t4.operation_id order by operation_id"

    df = pandas.DataFrame()
    df = pandas.read_sql(query, connection)
    categories = json.dumps(df['cropsname'].unique().tolist(), default=decimal_date_default)
    data = []
    for each in df['operation_id'].unique().tolist():
        data.append(df['percentage'][df['operation_id'] == each].tolist())


    # query for the 7 categories
    query = "with t as( select unnest(string_to_array(problemreletedinfo,' ')) id from data_info "+str(query_filter)+"), t1 as( select id,count(id) each_total from t group by id ), t2 as( select sum(each_total) total from t1 ) select id,round((each_total/total)*10,2) as percentage from t1,t2"
    df = pandas.DataFrame()
    df = pandas.read_sql(query,connection)
    seperate_categories = {}
    for i in range(8):
        seperate_categories[i] = 0
    for index,row in df.iterrows():
        seperate_categories[row['id']] = row['percentage']
    print(query)
    print(division)
    print(district)
    print(upazila)
    print(union)
    print(saoo_name)
    print(startdate)
    print(enddate)
    return HttpResponse(json.dumps({'data':data,'seperate_categories':seperate_categories}))


def getDistricts(request):
    division = json.loads(request.POST.get('div'))
    division = str(map(str, division))
    division =  division.replace('[', '(').replace(']', ')').replace("'",'')
    print division
    district_query = "select id,field_name from geo_info where loc_type = 2 and parent in " + str(division)
    district_data = json.dumps(__db_fetch_values_dict(district_query))
    return HttpResponse(district_data)

def getUpazilas(request):
    district = json.loads(request.POST.get('dist'))
    district = str(map(str, district))
    district =  district.replace('[', '(').replace(']', ')').replace("'",'')
    upazila_query = "select id,field_name from geo_info where loc_type = 3 and parent in " + str(district)
    upazila_data = json.dumps(__db_fetch_values_dict(upazila_query))
    return HttpResponse(upazila_data)


def getUnions(request):
    upazila = json.loads(request.POST.get('upz'))
    upazila = str(map(str, upazila))
    upazila =  upazila.replace('[', '(').replace(']', ')').replace("'",'')
    union_query = "select id,field_name from geo_info where loc_type = 4 and parent in " + str(upazila)
    union_data = json.dumps(__db_fetch_values_dict(union_query))
    return HttpResponse(union_data)

def getBlocks(request):
    union = json.loads(request.POST.get('union'))
    union = str(map(str, union))
    union =  union.replace('[', '(').replace(']', ')').replace("'",'')
    block_query = "select id,field_name from geo_info where loc_type = 5 and parent in " + str(union)
    block_data = json.dumps(__db_fetch_values_dict(block_query))
    return HttpResponse(block_data)

def getNames(request):
    block = json.loads(request.POST.get('block'))
    block = str(map(str, block))
    block =  block.replace('[', '(').replace(']', ')')
    print block
    names_query = "select distinct sender_id,(select username from users where id = sender_id::int) sender_name from data_info where union_name in " + str(block)+""
    # names_query = "select sender_id,(select username from auth_user where id::text = sender_id) sender_name from data_info where block_name = " + str(block)+"::text"
    names_data = json.dumps(__db_fetch_values_dict(names_query))
    return HttpResponse(names_data)


def xls_report_creator_for_daily_saoo_service_trend(request):
    divisions = request.POST.getlist('divisions')
    districts = request.POST.getlist('districts')
    upazilas = request.POST.getlist('upazilas')
    unions = request.POST.getlist('unions')
    # blocks = request.POST.getlist('blocks')
    saoo_names = request.POST.getlist('saoo_names')
    startdate = request.POST.getlist('startdate')
    enddate = request.POST.getlist('enddate')
    query = "SELECT id, data_id, i_start_time,(SELECT field_name FROM geo_info WHERE id::text = division and loc_type = 1) division, (SELECT field_name FROM geo_info WHERE id::text = district and loc_type = 2) district, (SELECT field_name FROM geo_info WHERE id::text = upazilla and loc_type = 3) upazilla, (SELECT field_name FROM geo_info WHERE id::text = union_name and loc_type = 4) union_name, (SELECT field_name FROM geo_info WHERE id::text = block_name and loc_type = 5) block_name, informationgroup, sdate, visitingplace, nameofvisitor, designationvisitor, mobile, gender, beneficialrytype, cropsname, problemreletedinfo, adviceno, advicepic, participantnumber, timespend, service_image, gps, i_end_time, (SELECT username FROM users WHERE id::text = sender_id) sender_name FROM PUBLIC.data_info where sdate BETWEEN '"+str(startdate[0])+"' and '"+str(enddate[0])+"' "
    if divisions[0] !='null' and divisions[0] !='':
        divisions = str(map(str, divisions))
        divisions = divisions.replace('[', '(').replace(']', ')')
        query += " and division in "+str(divisions)
    if districts[0] !='null'  and  districts[0] !='' :
        districts = str(map(str, districts))
        districts = districts.replace('[', '(').replace(']', ')')
        query += " and district in "+str(districts)
    if upazilas[0] !='null'  and  upazilas[0] !='':
        upazilas = str(map(str, upazilas))
        upazilas = upazilas.replace('[', '(').replace(']', ')')
        query += " and upazilla in "+str(upazilas)
    if unions[0] !='null'  and  unions[0] !='' :
        unions= str(map(str, unions))
        unions = unions.replace('[', '(').replace(']', ')')
        query += " and union_name in "+str(unions)
    # if blocks[0] !='null'  and  blocks[0] !='' :
    #     blocks = str(map(str, blocks))
    #     blocks = blocks.replace('[', '(').replace(']', ')')
    #     query += " and block_name in "+str(blocks)
    if saoo_names[0] !='null'  and  saoo_names[0] !='':
        saoo_names = str(map(str, saoo_names))
        saoo_names = saoo_names.replace('[', '(').replace(']', ')')
        query += " and sender_id in "+str(saoo_names)
    df = pandas.DataFrame()
    df = pandas.read_sql(query,connection)
    print(query)
    print(divisions)
    print districts
    print upazilas
    print unions
    # print blocks
    print saoo_names
    print startdate
    print enddate
    writer = pandas.ExcelWriter("onadata/media/uploaded_files/output.xlsx")
    df.to_excel(writer, sheet_name='Sheet1', index=False)
    writer.save()
    f = open('onadata/media/uploaded_files/output.xlsx', 'r')
    response = HttpResponse(f, mimetype='application/vnd.ms-excel')
    response['Content-Disposition'] = 'attachment; filename=SAOO Service Trend.xls'
    return response


def xls_report_creator_for_dst(request):
    divisions = request.POST.getlist('divisions')
    districts = request.POST.getlist('districts')
    upazilas = request.POST.getlist('upazilas')
    unions = request.POST.getlist('unions')
    # blocks = request.POST.getlist('blocks')
    saoo_names = request.POST.getlist('saoo_names')
    startdate = request.POST.getlist('startdate')
    enddate = request.POST.getlist('enddate')
    query = "SELECT id, data_id, i_start_time,(SELECT field_name FROM geo_info WHERE id::text = division and loc_type = 1) division, (SELECT field_name FROM geo_info WHERE id::text = district and loc_type = 2) district, (SELECT field_name FROM geo_info WHERE id::text = upazilla and loc_type = 3) upazilla, (SELECT field_name FROM geo_info WHERE id::text = union_name and loc_type = 4) union_name, (SELECT field_name FROM geo_info WHERE id::text = block_name and loc_type = 5) block_name, informationgroup, sdate, visitingplace, nameofvisitor, designationvisitor, mobile, gender, beneficialrytype, cropsname, problemreletedinfo, adviceno, advicepic, participantnumber, timespend, service_image, gps, i_end_time, (SELECT username FROM users WHERE id::text = sender_id) sender_name FROM PUBLIC.data_info where sdate BETWEEN '"+str(startdate[0])+"' and '"+str(enddate[0])+"' "
    if divisions[0] !='null' and divisions[0] !='':
        divisions = str(map(str, divisions))
        divisions = divisions.replace('[', '(').replace(']', ')')
        query += " and division in "+str(divisions)
    if districts[0] !='null'  and  districts[0] !='' :
        districts = str(map(str, districts))
        districts = districts.replace('[', '(').replace(']', ')')
        query += " and district in "+str(districts)
    if upazilas[0] !='null'  and  upazilas[0] !='':
        upazilas = str(map(str, upazilas))
        upazilas = upazilas.replace('[', '(').replace(']', ')')
        query += " and upazilla in "+str(upazilas)
    if unions[0] !='null'  and  unions[0] !='' :
        unions= str(map(str, unions))
        unions = unions.replace('[', '(').replace(']', ')')
        query += " and union_name in "+str(unions)
    # if blocks[0] !='null'  and  blocks[0] !='' :
    #     blocks = str(map(str, blocks))
    #     blocks = blocks.replace('[', '(').replace(']', ')')
    #     query += " and block_name in "+str(blocks)
    if saoo_names[0] !='null'  and  saoo_names[0] !='':
        saoo_names = str(map(str, saoo_names))
        saoo_names = saoo_names.replace('[', '(').replace(']', ')')
        query += " and sender_id in "+str(saoo_names)
    df = pandas.DataFrame()
    df = pandas.read_sql(query,connection)
    print(query)
    print(divisions)
    print districts
    print upazilas
    print unions
    # print blocks
    print saoo_names
    print startdate
    print enddate
    writer = pandas.ExcelWriter("onadata/media/uploaded_files/output.xlsx")
    df.to_excel(writer, sheet_name='Sheet1', index=False)
    writer.save()
    f = open('onadata/media/uploaded_files/output.xlsx', 'r')
    response = HttpResponse(f, mimetype='application/vnd.ms-excel')
    response['Content-Disposition'] = 'attachment; filename=Daily Service Trend.xls'
    return response

def test(request):
    response = urllib2.urlopen('http://localhost:8080/saoo/')
    html = response.read()
    data = json.loads(html)
    for key in data:
        print(data[key])
    return render(request, 'dashboardmodule/index.html')


