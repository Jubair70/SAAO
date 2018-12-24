from django.conf.urls import patterns, include, url
from django.contrib import admin
from onadata.apps.dashboardmodule import views

urlpatterns = patterns('',
    url(r'^$', views.test, name='index'),
url(r'^daily_service_trend/$', views.daily_service_trend, name='daily_service_trend'),
url(r'^daily_saoo_service_trend/$', views.daily_saoo_service_trend, name='daily_saoo_service_trend'),
url(r'^getDistricts/$', views.getDistricts, name='getDistricts'),
url(r'^getUpazilas/$', views.getUpazilas, name='getUpazilas'),
url(r'^getUnions/$', views.getUnions, name='getUnions'),
url(r'^getBlocks/$', views.getBlocks, name='getBlocks'),
url(r'^getNames/$', views.getNames, name='getNames'),
url(r'^data_filter/$', views.data_filter, name='data_filter'),
url(r'^data_filter_DST/$', views.data_filter_DST, name='data_filter_DST'),
url(r'^xls_report_creator_for_daily_saoo_service_trend/$', views.xls_report_creator_for_daily_saoo_service_trend, name='xls_report_creator_for_daily_saoo_service_trend'),
url(r'^xls_report_creator_for_dst/$', views.xls_report_creator_for_dst, name='xls_report_creator_for_dst'),
    )
