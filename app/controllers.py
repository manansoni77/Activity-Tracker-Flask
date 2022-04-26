from click import option
from flask import request, current_app as app, render_template, session, redirect, url_for, send_file
from datetime import datetime, timedelta
from app.models import credentials, user, trackers, logs, db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, login_required
import re
import os
from sqlalchemy import desc
import random
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as plticker
import pandas as pd


def ran_color():
    colors = ['mediumpurple','lightcoral','lemonchiffon','lightskyblue','palegreen','peachpuff','paleturquoise']
    t = random.choice(colors)
    print(t)
    return t


def to_timedelta(time):
    tmp = datetime.strptime(time,"%H:%M:%S")
    return timedelta(hours=tmp.hour,minutes=tmp.minute)


code_time = '%Y-%m-%dT%H:%M'
format = "%d-%m-%Y %H:%M:%S"
@app.template_filter()
def format_time(time):
    return datetime.strftime(time,format)
@app.template_filter()
def format_time_code(time):
    return datetime.strftime(time,code_time)


login_re = re.compile(r'[^a-zA-Z0-9$]').search
password_re = re.compile(r'[^a-zA-Z0-9$]').search
options_re = re.compile(r'[^a-zA-Z0-9 !?]').search
text_re = re.compile(r'[^a-zA-Z0-9 !?]').search


@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response


@app.route('/',methods=['GET'])
def home():
    return redirect(url_for('dashboard'))


@app.route('/login',methods=['GET','POST'])
def login():
    # POST
    if request.method == 'POST':
        login_id = request.form.get('login_id')
        password = request.form.get('password')
        if bool(login_re(login_id)) or bool(password_re(password)):
            return render_template('login.html',message='Please use only a-z A-Z 0-9 or $')
        check_cred = credentials.query.filter_by(login_id=login_id).first()
        if check_cred:
            if check_password_hash(check_cred.password, password):
                check_user = user.query.filter_by(user_id=check_cred.user_id).first()
                login_user(check_user,remember=True)
                session['user_id'] = check_user.user_id
                session['user_first_name'] = check_user.first_name
                session['user_last_name'] = check_user.last_name
                session['dob'] = check_user.dob
                return redirect(url_for('dashboard'))
            else:
                return render_template('login.html',message='Wrong Password!')
        else:
            return render_template('login.html',message='User Does Not Exist!')
    # GET
    elif request.method == 'GET':
        return render_template('login.html')


@app.route('/signup',methods=['GET','POST'])
def signup():
    # POST
    if request.method == 'POST':
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        if not first_name.isalpha() or not last_name.isalpha():
            return render_template('signup.html',message='Please use only alphabets for names!')
        dob = request.form.get('dob')
        login_id = request.form.get('login_id')
        password = request.form.get('password')
        if bool(login_re(login_id)) or bool(password_re(password)):
            return render_template('signup.html',message='Please use only a-z A-Z 0-9 or $')
        check_cred = credentials.query.filter_by(login_id=login_id).first()
        if check_cred:
            return render_template('signup.html',message='User with that login already exists!')
        else:
            new_user = user(first_name=first_name,last_name=last_name,dob=dob)
            db.session.add(new_user)
            db.session.commit()
            new_cred = credentials(login_id=login_id,password=generate_password_hash(password,method='sha256'),user_id=new_user.user_id)
            db.session.add(new_cred)
            db.session.commit()
            return redirect('/login')
    # GET
    elif request.method == 'GET':
        return render_template('signup.html')


@app.route('/logout',methods=['GET'])
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route("/dashboard",methods=["GET"])
@login_required
def dashboard():
    user_details = user.query.filter_by(user_id=session['user_id']).first()
    added_trackers = trackers.query.filter_by(user_id=session['user_id']).all()
    last_logs = []
    for tracker in added_trackers:
        last_log = logs.query.filter_by(track_id=tracker.track_id).order_by(desc(logs.time)).first()
        last_logs.append(last_log)
    return render_template('dashboard.html',tracks=added_trackers,user=user_details,logs=last_logs)


@app.route('/tracker/<int:track_id>',methods=['GET'])
@login_required
def tracker(track_id):
    if request.method == 'GET':
        tracker = trackers.query.filter_by(track_id=track_id).first()
        tracker_logs = logs.query.filter_by(track_id=track_id).all()
        val = []
        time = []
        plot = True
        plot_message = ""
        for log in tracker_logs:
            val.append(log.info)
            time.append(log.time.date())
        if not tracker_logs:
            plot_message = "No Logs Available To Plot Yet"
            plot = False
        else:
            fig, ax = plt.subplots(figsize=(5,5))
            df = pd.DataFrame({'time':time,'val':val})
            if tracker.track_type == 'num':
                df['val'] = df['val'].astype(int)
                plot_df = df.groupby(['time']).sum()
                ax.set_title(f'{tracker.track_name} Graph')
                ax.set_ylabel(f'{tracker.options}')
                ax.set_xlabel('Date')
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
                ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))
                ax.bar(plot_df.index,plot_df['val'],color=ran_color())
            elif tracker.track_type == 'time':
                df['val'] = df.apply(lambda row : to_timedelta(row['val']),axis=1)
                plot_df = df.groupby(['time']).sum()
                plot_df['val'] = plot_df['val'].astype('timedelta64[m]')
                ax.set_title(f'{tracker.track_name} Graph')
                ax.set_ylabel('Time Duration (Minutes)')
                ax.set_xlabel('Date')
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
                ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))
                ax.bar(plot_df.index,plot_df['val'],color=ran_color())
            elif tracker.track_type == 'mcq':
                freq = df['val'].value_counts()
                labels = []
                data = []
                for l,d in freq.iteritems():
                    print(l,d)
                    labels.append(l)
                    data.append(d)
                ax.pie(data,labels=labels)
            elif tracker.track_type == 'bool':
                print(tracker.options)
                labels = tracker.options.split(',')
                freq = {key: 0 for key in labels}
                for i in df['val']:
                    freq[i]+=1
                data = []
                for label in labels:
                    data.append(freq[label])
                ax.set_ylabel('Count')
                ax.yaxis.set_major_locator(plticker.MultipleLocator(base=1))
                ax.bar(labels,data,color=ran_color())
            fig.savefig(f'static/{track_id}.png')
        return render_template('tracker.html',track=tracker,logs=tracker_logs,plot=plot,plot_message=plot_message)


@app.route('/getcsv/<int:track_id>',methods=['GET'])
@login_required
def getcsv(track_id):
    if request.method == 'GET':
        track = trackers.query.filter_by(track_id=track_id).first()
        tracker_logs = logs.query.filter_by(track_id=track_id).all()
        val = []
        time = []
        for log in tracker_logs:
            val.append(log.info)
            time.append(log.time)
        df = pd.DataFrame({'time':time,'val':val})
        df.to_excel('outputs/tmp.xlsx')
        return send_file('outputs/tmp.xlsx',mimetype='text/xlsx',attachment_filename=f"{session['user_first_name']}-{track.track_name}.xlsx",as_attachment=True)


@app.route('/add_tracker',methods=['GET','POST'])
@login_required
def add_tracker():
    # GET
    if request.method == 'GET':
        return render_template('add_tracker.html')
    # POST
    elif request.method == 'POST':
        track_name = request.form.get('track_name')
        track_desc = request.form.get('track_desc')
        if text_re(track_name) or text_re(track_desc):
            return render_template('add_tracker.html',message='Please use only alphabets or numbers in track name and description!')
        track_type = request.form.get('track_type')
        options = request.form.get('options')
        check_track = trackers.query.filter_by(track_name=track_name,user_id=session['user_id']).first()
        if check_track:
            return render_template('add_tracker.html',message='This track name is already in your list of trackers!')
        if track_type=='num':
            if options == "":
                return render_template('add_tracker.html',message='Please don\'t leave options empty!')
            if bool(options_re(options)):
                return render_template('add_tracker.html',message='Please use only alphabets, numbers, !, ?')
        elif track_type=='mcq':
            opt_list = options.split(',')
            print(opt_list)
            if opt_list[0] == "":
                return render_template('add_tracker.html',message='Please don\'t leave options empty!')
            for item in opt_list:
                if bool(options_re(item)):
                    return render_template('add_tracker.html',message='Please use only alphabets, numbers, !, ? and make sure they are seperated using only comma')
        elif track_type=='time':
            if bool(options_re(options)):
                return render_template('add_tracker.html',message='Please use only alphabets, numbers, !, ?')
        elif track_type=='bool':
            opt_list = options.split(',')
            if opt_list[0] == "":
                return render_template('add_tracker.html',message='Please don\'t leave options empty!')
            if len(opt_list)!=2:
                return render_template('add_tracker.html',message='Please enter only 2 comma seperated options')
            for item in opt_list:
                if bool(options_re(item)):
                    return render_template('add_tracker.html',message='Please use only alphabets, numbers, !, ? and make sure they are seperated using only comma')
        new_track = trackers(user_id=session['user_id'],track_name=track_name,track_desc=track_desc,track_type=track_type,options=options)
        db.session.add(new_track)
        db.session.commit()
        return redirect(url_for('dashboard'))


@app.route('/edit_tracker/<int:track_id>',methods=['GET','POST'])
@login_required
def edit_tracker(track_id):
    if request.method == 'GET':
        tracker = trackers.query.filter_by(track_id=track_id).first()
        return render_template("edit_tracker.html",tracker=tracker)
    elif request.method == 'POST':
        tracker = trackers.query.filter_by(track_id=track_id).first()
        track_name = request.form.get('track_name')
        track_desc = request.form.get('track_desc')
        if text_re(track_name) or text_re(track_desc):
            return render_template("edit_tracker.html",tracker=tracker,message='Please use only alphabets or numbers in track name and description!')
        track_type = tracker.track_type
        print(track_type)
        options = request.form.get('options')
        if track_type=='num':
            if options == "":
                return render_template('edit_tracker.html',tracker=tracker,message='Please don\'t leave options empty!')
            if bool(options_re(options)):
                return render_template("edit_tracker.html",tracker=tracker,message='Please use only alphabets, numbers, !, ?')
        elif track_type=='mcq':
            opt_list = options.split(',')
            print(opt_list)
            if opt_list[0] == "":
                return render_template('edit_tracker.html',tracker=tracker,message='Please don\'t leave options empty!')
            for item in opt_list:
                if bool(options_re(item)):
                    return render_template("edit_tracker.html",tracker=tracker,message='Please use only alphabets, numbers, !, ? and make sure they are seperated using only comma')
        elif track_type=='time':
            if bool(options_re(options)):
                return render_template("edit_tracker.html",tracker=tracker,message='Please use only alphabets, numbers, !, ?')
        elif track_type=='bool':
            opt_list = options.split(',')
            if opt_list[0] == "":
                return render_template('edit_tracker.html',tracker=tracker,message='Please don\'t leave options empty!')
            if len(opt_list)!=2:
                return render_template("edit_tracker.html",tracker=tracker,message='Please enter only 2 comma seperated options')
            for item in opt_list:
                if bool(options_re(item)):
                    return render_template("edit_tracker.html",tracker=tracker,message='Please use only alphabets, numbers, !, ? and make sure they are seperated using only comma')
        tracker.track_name = track_name
        tracker.track_desc = track_desc
        tracker.options = options
        db.session.commit()
        return redirect(url_for('dashboard'))


@app.route('/delete_tracker/<int:track_id>',methods=['GET'])
@login_required
def delete_tracker(track_id):
    if request.method == 'GET':
        trackers.query.filter_by(track_id=track_id).delete()
        logs.query.filter_by(track_id=track_id).delete()
        db.session.commit()
        if os.path.exists(f'static/{track_id}.png'):
            os.remove(f'static/{track_id}.png')
        return redirect(url_for('dashboard'))


@app.route('/log/<int:track_id>',methods=['GET','POST'])
@login_required
def log(track_id,message=""):
    if request.method == 'GET' or message:
        tracker = trackers.query.filter_by(track_id=track_id).first()
        if tracker.track_type == 'num':
            units = tracker.options
            return render_template('log.html',tracker=tracker,units=units,message=message)
        elif tracker.track_type=='mcq':
            opt_list = tracker.options.split(',')
            return render_template('log.html',tracker=tracker,options=opt_list,message=message)
        elif tracker.track_type=='time':
            return render_template('log.html',tracker=tracker,message=message)
        elif tracker.track_type=='bool':
            opt_list = tracker.options.split(',')
            return render_template('log.html',tracker=tracker,options=opt_list,message=message)
    if request.method == 'POST':
        tracker = trackers.query.filter_by(track_id=track_id).first()
        if tracker.track_type == 'time':
            start = datetime.strptime(request.form.get('start'),code_time)
            end = datetime.strptime(request.form.get('end'),code_time)
            if end<=start:
                return log(track_id=tracker.track_id,message='Time duration is negative or zero!')
            elif (end-start).days:
                return log(track_id=tracker.track_id,message='Time duration is more than one day!')
            val = str(end-start)
            time = datetime.strptime(request.form.get('start'),code_time)
        else:
            val = request.form.get('val')
            time = datetime.strptime(request.form.get('time'),code_time)
        if tracker.track_type == 'num':
            if not val.isnumeric():
                return render_template('log.html',message='Value entered is not numeric!')
        new_log = logs(track_id=tracker.track_id,info=val,time=time)
        db.session.add(new_log)
        db.session.commit()
        return redirect(url_for('tracker',track_id=tracker.track_id))


@app.route('/edit_log/<int:track_id>/<logtime>',methods=['GET','POST'])
@login_required
def edit_log(track_id,logtime,message=""):
    if type(logtime) == str:
        logtime = datetime.strptime(logtime,format)
    if request.method == 'GET' or message:
        tracker = trackers.query.filter_by(track_id=track_id).first()
        log = logs.query.filter_by(track_id=track_id,time=logtime).first()
        if tracker.track_type == 'time':
            start = log.time
            tmp = datetime.strptime(log.info, "%H:%M:%S")
            delta = timedelta(hours=tmp.hour,minutes=tmp.minute)
            log.info = datetime.strftime(start+delta,code_time)
        return render_template('edit_log.html',log=log,tracker=tracker,message=message,options=tracker.options.split(','))
    if request.method == 'POST':
        tracker = trackers.query.filter_by(track_id=track_id).first()
        if tracker.track_type == 'time':
            start = datetime.strptime(request.form.get('start'),code_time)
            end = datetime.strptime(request.form.get('end'),code_time)
            if end<=start:
                return edit_log(track_id=tracker.track_id,logtime=logtime,message='Time duration is negative or zero!')
            elif (end-start).days:
                return edit_log(track_id=tracker.track_id,logtime=logtime,message='Time duration is more than one day!')
            val = str(end-start)
            time = datetime.strptime(request.form.get('start'),code_time)
        else:
            val = request.form.get('val')
            time = datetime.strptime(request.form.get('time'),code_time)
        if tracker.track_type == 'num':
            if not val.isnumeric():
                return render_template('log.html',message='Value entered is not numeric!')
        print(val,time)
        log = logs.query.filter_by(track_id=track_id,time=logtime).first()
        log.info = val
        log.time = time
        db.session.commit()
        return redirect(url_for('tracker',track_id=track_id))


@app.route('/del_log/<int:track_id>/<time>',methods=['GET'])
@login_required
def del_log(track_id,time):
    time = datetime.strptime(time,format)
    if request.method == 'GET':
        logs.query.filter_by(track_id=track_id,time=time).delete()
        db.session.commit()
        return redirect(url_for('tracker',track_id=track_id))