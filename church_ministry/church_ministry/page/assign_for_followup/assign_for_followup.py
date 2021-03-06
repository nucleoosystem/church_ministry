# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals
import frappe
import frappe.defaults
from frappe.desk.reportview import get_match_cond
import frappe.share
from frappe.utils import cstr,now,add_days,nowdate
from erpnext.setup.doctype.sms_settings.sms_settings import send_sms
import json
from gcm import GCM

@frappe.whitelist()
def get_ftv_member():
	roles=frappe.get_roles(frappe.user.name)
	val=frappe.db.sql("select defkey,defvalue from `tabDefaultValue` where defkey in ('Cells','Senior Cells','PCFs','Churches','Group Churches','Zones','Regions') and parent='%s' limit 1"%(frappe.user.name),as_list=1)
	# frappe.errprint(val)
	if val:
		if val[0][0]=='Cells':
			key='cell'
			value=val[0][1]
		elif val[0][0]=='Senior Cells':
			key='senior_cell'
			value=val[0][1]
		elif val[0][0]=='PCFs':
			key='pcf'
			value=val[0][1]
		elif val[0][0]=='Churches':
			key='Church'
			value=val[0][1]
		elif val[0][0]=='Group Churches':
			key='church_group'
			value=val[0][1]
		elif val[0][0]=='Zones':
			key='zone'
			value=val[0][1]
		elif val[0][0]=='Regions':
			key='region'
			value=val[0][1]
		return{
			"key" : key,
			"value" : value
		}
	else:
		return{
			"key" : 1,
			"value" : 1
		}	


@frappe.whitelist()
def ftv():
	ftv_member = get_ftv_member()
	if ftv_member:
		return {
			"ftv": [d[0] for d in frappe.db.sql("select name,ftv_name from `tabFirst Timer` t where (ftv_owner is null or ftv_owner='') and  not exists (select ftv_id_no from tabMember where ftv_id_no=t.name) and %s='%s'"%(ftv_member['key'],ftv_member['value']))]
		}
	else:
		return {
			"ftv": [d[0] for d in frappe.db.sql("select name from `tabFirst Timer` t where (ftv_owner is null or ftv_owner='') and  not exists (select ftv_id_no from tabMember where ftv_id_no=t.name)")]
		}

@frappe.whitelist()
def loadftv(doctype, txt, searchfield, start, page_len, filters):
	    	#frappe.errprint(get_match_cond(doctype))
		return frappe.db.sql("""select name,ftv_name from `tabFirst Timer` where (ftv_owner is null or ftv_owner='')  and name NOT IN (select ifnull(ftv_id_no,'') from tabMember)
			and ({key} like %(txt)s
				or ftv_name like %(txt)s)
			{mcond}
		order by
			if(locate(%(_txt)s, name), locate(%(_txt)s, name), 99999),
			if(locate(%(_txt)s, ftv_name), locate(%(_txt)s, ftv_name), 99999),
			name, ftv_name
		limit %(start)s, %(page_len)s""".format(**{
			'key': searchfield,
			'mcond': get_match_cond(doctype)
		}), {
			'txt': "%%%s%%" % txt,
			'_txt': txt.replace("%", ""),
			'start': start,
			'page_len': page_len
		})


@frappe.whitelist()
def ftvdetails(ftv):
	ftv_member = get_ftv_member()
	if ftv_member:
		query="select ftv_name,sex,YEAR(CURDATE()) - YEAR(date_of_birth)- (DATE_FORMAT(CURDATE(), '%m%d') < DATE_FORMAT(date_of_birth, '%m%d')) as age,address,age_group from `tabFirst Timer` where name='"+ftv+"' and %s='%s'"%(ftv_member['key'],ftv_member['value'])
		return {
			"ftv": [frappe.db.sql(query)]
		}
	else:
		query="select ftv_name,sex,YEAR(CURDATE()) - YEAR(date_of_birth)- (DATE_FORMAT(CURDATE(), '%m%d') < DATE_FORMAT(date_of_birth, '%m%d')) as age,address,age_group from `tabFirst Timer` where name='"+ftv+"'"
		return {
			"ftv": [frappe.db.sql(query)]
		}

@frappe.whitelist()
def loadmembers(ftv):
	ftv_member = get_ftv_member()
	ft_dtl=frappe.db.sql("select sex,age_group,lat,lon from `tabFirst Timer` where name='%s'"%ftv)
	#frappe.errprint(ft_dtl)
	if ftv_member:
		#a="select b.name,b.member_name,b.sex,YEAR(CURDATE()) - YEAR(b.date_of_birth)- (DATE_FORMAT(CURDATE(), '%m%d') < DATE_FORMAT(b.date_of_birth, '%m%d')) as age,round(6371 * 2 * ASIN(SQRT(POWER(SIN((a.lat - abs(b.lat)) * pi()/180 / 2),2) + COS(a.lat * pi()/180 ) * COS(abs(b.lat) * pi()/180) * POWER(SIN((a.lon - a.lon) * pi()/180 / 2), 2) )),6) as distance from  `tabFirst Timer` a,`tabMember` b where b.is_eligibale_for_follow_up=1 and a.name='"+ftv+"' and %s='%s' order by distance asc ,age desc "%(ftv_member['key'],ftv_member['value'])
		b="""select name,member_name,sex,age_group,distance from ( SELECT b.name,b.member_name,b.sex,ROUND(6371 * 2 * ASIN(SQRT(POWER(SIN((coalesce(nullif('%s','lat'),0) - ABS(b.lat)) * pi()/180 / 2),2) + COS(coalesce(nullif('%s','lat'),0) * pi()/180 ) * COS(ABS(b.lat) * pi()/180) * POWER(SIN((coalesce(nullif('%s','lon'),0) - coalesce(nullif('%s','lon'),0)) * pi()/180 / 2), 2) )),6) as distance,case when '%s'=b.sex then 1 else 0 end as gender_rank,b.age_group FROM `tabMember` b WHERE b.is_eligibale_for_follow_up=1 and b.age_group='%s' )foo order by distance asc,gender_rank asc """  %(ft_dtl[0][2],ft_dtl[0][2],ft_dtl[0][3],ft_dtl[0][3],ft_dtl[0][0],ft_dtl[0][1])
		#frappe.errprint(b)
		return {
			"members": [frappe.db.sql(b)]
		}
	else:
		#a="select b.name,b.member_name,b.sex,YEAR(CURDATE()) - YEAR(b.date_of_birth)- (DATE_FORMAT(CURDATE(), '%m%d') < DATE_FORMAT(b.date_of_birth, '%m%d')) as age,round(6371 * 2 * ASIN(SQRT(POWER(SIN((a.lat - abs(b.lat)) * pi()/180 / 2),2) + COS(a.lat * pi()/180 ) * COS(abs(b.lat) * pi()/180) * POWER(SIN((a.lon - a.lon) * pi()/180 / 2), 2) )),6) as distance from  `tabFirst Timer` a,`tabMember` b where b.is_eligibale_for_follow_up=1 and a.name='"+ftv+"' order by distance asc ,age desc "
		b="""select name,member_name,sex,age_group,distance from ( SELECT b.name,b.member_name,b.sex,ROUND(6371 * 2 * ASIN(SQRT(POWER(SIN((coalesce(nullif('%s','lat'),0) - ABS(b.lat)) * pi()/180 / 2),2) + COS(coalesce(nullif('%s','lat'),0) * pi()/180 ) * COS(ABS(b.lat) * pi()/180) * POWER(SIN((coalesce(nullif('%s','lon'),0) - coalesce(nullif('%s','lon'),0)) * pi()/180 / 2), 2) )),6) as distance,case when '%s'=b.sex then 1 else 0 end as gender_rank,b.age_group FROM `tabMember` b WHERE b.is_eligibale_for_follow_up=1 and b.age_group='%s' )foo order by distance asc,gender_rank asc """   %(ft_dtl[0][2],ft_dtl[0][2],ft_dtl[0][3],ft_dtl[0][3],ft_dtl[0][0],ft_dtl[0][1])
		#frappe.errprint(b)
		return {
			"members": [frappe.db.sql(b)]
		}


@frappe.whitelist()
def assignmember(memberid,ftv):
	frappe.db.sql("""update `tabFirst Timer` set ftv_owner='%s' where name='%s' """ % (memberid,ftv))
	# recipients='gangadhar.k@indictranstech.com'
	member=frappe.db.sql("select member_name,email_id,phone_1 from `tabMember` where name='%s'"%(memberid))
	member_ph = frappe.db.sql("select phone_1 from `tabMember` where name='%s'"%(memberid))
	ftvdetails=frappe.db.sql("select ftv_name,email_id,task_description,due_date,phone_1 from `tabFirst Timer` where name='%s'"%(ftv))
	ftv_ph = frappe.db.sql("select phone_1 from `tabMember` where name='%s'"%(ftv))

	msg_member="""Hello %s,\n The First Timer '%s' name: '%s' Email ID: '%s' is assigned to you for follow up.\n Regards,\n Verve
	"""%(member[0][0],ftv,ftvdetails[0][0],ftvdetails[0][1])
	
	msg_ftv="""Hello %s,\n The Member '%s' name: '%s' Email ID: '%s' is assigned to you for follow up.\n Regards, \n Verve
	"""%(ftvdetails[0][0],memberid,member[0][0],member[0][1])
	
	desc="""Member '%s' is assigned to First Timer '%s' for followup."""%(memberid,ftv)
	
	task=frappe.get_doc({
				"doctype": "Task",
				"subject": "Assign For followup",
				"expected_start_date":nowdate(),
				"expected_start_date":add_days(nowdate(),2),
				"status": "Open",
				"project": "",
				"description":desc
			}).insert(ignore_permissions=True)

	if frappe.db.exists("User", ftvdetails[0][1]):
		frappe.share.add("Task", task.name, ftvdetails[0][1], write=0)
	if frappe.db.exists("User", member[0][1]):	
		frappe.share.add("Task", task.name, member[0][1], write=1)

	notify = frappe.db.sql("""select value from `tabSingles` where doctype='Notification Settings' and field='assign_for_followup'""",as_list=1)
	if "Email" in notify[0][0]:
		if member:
			frappe.sendmail(recipients=member[0][1], content=msg_member, subject='Assign For FollowUp Notification')
		if ftvdetails:
			frappe.sendmail(recipients=ftvdetails[0][1], content=msg_ftv, subject='Assign For FollowUp Notification')
	if "SMS" in notify[0][0]:
		if member_ph:
			send_sms(member_ph[0], msg_member)
		if ftv_ph:
			send_sms(ftv_ph[0], msg_ftv)
	if "Push Notification" in notify[0][0]:
		data={}
		data['Message']=msg_member
		gcm = GCM('AIzaSyBIc4LYCnUU9wFV_pBoFHHzLoGm_xHl-5k')
		res=frappe.db.sql("select device_id from tabUser where name ='%s'" %(member[0][1]),as_list=1)
		frappe.errprint(res)
		if res:
			res = gcm.json_request(registration_ids=res, data=data,collapse_key='uptoyou', delay_while_idle=True, time_to_live=3600)

	# receiver_list=[]
	# receiver_list.append(member[0][2])
	# frappe.errprint(['rev[0]',receiver_list[0]])
	# if receiver_list[0] :
	# 	frappe.errprint(receiver_list[0])
	# 	send_sms(receiver_list, cstr(msg_member))	
	# frappe.sendmail(recipients=member[0][1], sender='gangadhar.k@indictranstech.com', content=msg_member, subject='Assign for follow up')
	# frappe.sendmail(recipients=ftvdetails[0][1], sender='gangadhar.k@indictranstech.com', content=msg_ftv, subject='Assign for follow up')
	return "Done"
