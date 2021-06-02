import os
import shutil
import csv
import sys
from flask import Flask,render_template, url_for, flash, redirect, request
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from flask_uploads import UploadSet, configure_uploads, IMAGES, patch_request_class
from flask_bootstrap import Bootstrap
from wtforms import StringField, IntegerField, SubmitField, SelectField
from wtforms.validators import DataRequired
import pandas as pd
from sqlalchemy import text	
from sqlalchemy import create_engine
from datetime import datetime			
import pandas as pd
import time

app = Flask(__name__)
bootstrap = Bootstrap(app)

# Configurations
app.config['SECRET_KEY'] = 'blah blah blah blah'





# procure vaccines from manufacturer
class ProcureForm(FlaskForm):
	lot = IntegerField('Enter Lot ID')
	state = StringField('State')
	submit = SubmitField('Submit')

@app.route('/',methods=['GET','POST'])
@app.route('/procure',methods=['GET','POST'])
def procure():
	form = ProcureForm()
	engine = create_engine("mysql+pymysql://{user}:{pw}@acadmysqldb001p.uta.edu/{db}"
                       .format(user="",
                               pw="",
                               db=""))
	dbConnection    = engine.connect()
	if form.validate_on_submit():
		lot = int(form.lot.data)
		statee = form.state.data.capitalize()

		query = "SELECT * from MANUFACTURED_DOSE where lot_Id = %s"
		df1 = pd.read_sql(query, dbConnection, params=[lot]);

		vac_type = ""
		df_temp = df1.copy().iloc[:, 4:]
		for x in df_temp.loc[0, :].values.tolist():
			try:
				if len(x)!=0:
					vac_type = x
			except:
  				print("Variable x is not defined")	

		# inserting into federal
		now = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
		data = ( { "date_Proc" :now, "incoming_Lot_Id": lot,"manuf_Name":df1["manuf_Name"], "state": statee, "dose_Proc_Count": df1["doses_Count"], "vaccine_Type":vac_type, "date_Manuf":df1["date_Manuf"] } )
		df_fed = pd.DataFrame(data)
		df_fed.to_sql('FEDERAL', con = engine, if_exists = 'append', chunksize = 1000, index=False)


		# entering data into state
		data = ( { "vaccine_Type":vac_type, "manuf_Name":df1["manuf_Name"], "state": statee, "received_Datetime" :now, "received_Count": df1["doses_Count"] } )
		df_state = pd.DataFrame(data)
		df_state.to_sql('STATE_DISTR', con = engine, if_exists = 'append', chunksize = 1000, index=False)

		# gather all data from Manufacturer
		query = "SELECT * from MANUFACTURED_DOSE WHERE lot_Id <> %s"
		df2 = pd.read_sql(query, dbConnection, params=[lot]);

		return render_template('procure.html', form=form,  result=[df1.to_html(classes='data', header="true")], results=[df2.to_html(classes='data', header="true")])

	query = "SELECT * from MANUFACTURED_DOSE"
	df           = pd.read_sql(query, dbConnection);
	return render_template('procure.html', form=form, results=[df.to_html(classes='data', header="true")])




# distribute to state
class StateDistributeForm(FlaskForm):
	count = IntegerField('Number of vaccines:')
	state = StringField('State')
	vac_type = StringField('Type of Vaccine:')
	manu = StringField('Manufacturer:')
	submit = SubmitField('Distribute to State')

@app.route('/statedistribution',methods=['GET','POST'])
def statedistribution():
	form = StateDistributeForm()
	engine = create_engine("mysql+pymysql://{user}:{pw}@acadmysqldb001p.uta.edu/{db}"
                       .format(user="",
                               pw="",
                               db=""))
	dbConnection    = engine.connect()
	if form.validate_on_submit():
		count = int(form.count.data)
		state = form.state.data.capitalize()
		manu = form.manu.data.capitalize()
		vac_type = form.vac_type.data.capitalize()

		# entering data into state
		now = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
		data = ( { "vaccine_Type":vac_type, "manuf_Name":manu, "state": state, "received_Datetime" :now, "received_Count": count } )
		df_state = pd.DataFrame(data, index=[0])
		df_state.to_sql('STATE_DISTR', con = engine, if_exists = 'append', chunksize = 1000, index=False)

		return render_template('statedistribute.html', form=form, result = "Distributed", count= count, state = state)
	return render_template('statedistribute.html', form=form)





# disrtribute to local bodies
class StateToUnitForm(FlaskForm):
	unit = StringField('Unit')
	state = StringField('State')
	count = IntegerField('Count')
	submit = SubmitField('Distribute')

@app.route('/unitdistribute',methods=['GET','POST'])
def unitdistribute():
	form = StateToUnitForm()
	engine = create_engine("mysql+pymysql://{user}:{pw}@acadmysqldb001p.uta.edu/{db}"
                       .format(user="",
                               pw="",
                               db=""))
	dbConnection    = engine.connect()
	if form.validate_on_submit():
		unit = form.unit.data.capitalize()
		state = form.state.data.capitalize()
		count = form.count.data

		now = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
		data = ( { "vaccine_Count": count, "unit_Name": unit, "date_Distr" :now, "state":state } )
		df_unit = pd.DataFrame(data, index=[0])
		df_unit.to_sql('VACCINE_DISTR', con = engine, if_exists = 'append', chunksize = 1000, index=False)
		
		return render_template('distribute.html', form=form,  result=" vaccines distributed to ", unit=unit, state = state, count= count)

	return render_template('distribute.html', form=form)




# vaccination
class VaccinationForm(FlaskForm):
	state = StringField('State')
	unit = StringField('Unit')
	dose = IntegerField('Is it dose 1 or 2?')
	pname = StringField('Patient name')
	paddr = StringField('Address')
	pcontact = IntegerField('Contact')
	page = IntegerField('Age')
	pallergy = StringField('Any allergies?')
	pid = IntegerField('Patient ID')
	pmed = StringField('Any Side Effect after Dose 1?')
	submit = SubmitField('Submit')

@app.route('/vaccination',methods=['GET','POST'])
def vaccination():
	form = VaccinationForm()
	engine = create_engine('mysql+pymysql://root:Vadakkedath@2021@localhost/')
	dbConnection    = engine.connect()
	if form.validate_on_submit():
		unit = form.unit.data.capitalize()
		state = form.state.data.capitalize()
		dose = form.dose.data
		pname = form.pname.data.capitalize()
		paddr = form.paddr.data.capitalize()
		pcontact = form.pcontact.data
		page = form.page.data
		pallergy = form.pallergy.data.capitalize()
		pid = form.pid.data
		pmed = form.pmed.data.capitalize()

		now = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
		if dose ==1:
			dose1 = 1
			dose2=0
			data = ( { "unit_Name": unit, "date_Distr" :now, "state":state, "dose1": dose1, "dose2": dose2, "p_Name": pname, "p_Addr": paddr, "p_Contact": pcontact,  "p_Age":page, "p_Allergy_hist":pallergy, "p_Id":pid, "p_Medical_Cond":pmed} )
		if dose ==2:
			dose1 = 1
			dose2=1
			data = ( { "unit_Name": unit, "date_Distr" :now, "state":state, "dose1": dose1, "dose2": dose2, "p_Name": pname, "p_Addr": paddr, "p_Contact": pcontact,  "p_Age":page, "p_Allergy_hist":pallergy, "p_Id":pid, "p_Medical_Cond":pmed} )
		df_unit = pd.DataFrame(data, index=[0])
		df_unit.to_sql('VACCINE_DISTR', con = engine, if_exists = 'append', chunksize = 1000, index=False)
		
		return render_template('vaccination.html', form=form,  result="Vaccine given to ", name = pname, id = pid)

	return render_template('vaccination.html', form=form)





# sied effects

class SideeffectForm(FlaskForm):
	pid = IntegerField('Patient ID')
	dose = IntegerField('What is the latest dose received by the patient 1 or 2?')
	effect = StringField('What are the Side Effects Occured?')
	submit = SubmitField('Submit')

@app.route('/sideeffect',methods=['GET','POST'])
def sideeffect():
	form = SideeffectForm()
	engine = create_engine("mysql+pymysql://{user}:{pw}@acadmysqldb001p.uta.edu/{db}"
                       .format(user="",
                               pw="",
                               db=""))
	dbConnection    = engine.connect()
	if form.validate_on_submit():
		pid = form.pid.data
		dose = form.dose.data
		effect = form.effect.data.capitalize()
		
		if dose == 1:
			sql = """
			   	UPDATE VACCINE_DISTR
			    SET p_Medical_Cond = %(effect)s
			    WHERE p_Id = %(pid)s AND dose2 = 0 AND dose1 = 1
			"""

		if dose == 2:
			sql = """
			    UPDATE VACCINE_DISTR
			    SET p_Medical_Cond = %(effect)s
			    WHERE p_Id = %(pid)s AND dose2 = 1 AND dose1 = 1
			"""

		with engine.begin() as conn:     # TRANSACTION
		    conn.execute(sql, {"effect": effect, "pid":pid})


		return render_template('sideeffect.html', form=form,  result="Side effect occured to ", id = pid, dose=dose)

	return render_template('sideeffect.html', form=form)


@app.route('/notification',methods=['GET','POST'])
def notification():
	engine = create_engine('mysql+pymysql://root:@localhost/')
	dbConnection    = engine.connect()

	query = "SELECT * from cdc_notif_invalid_phase"
	df = pd.read_sql(query, dbConnection);
	return render_template('notification.html', results=[df.to_html(classes='data', header="true")])



port = int(os.getenv('PORT', '3000'))
app.run(host='0.0.0.0', port=port, debug=True)