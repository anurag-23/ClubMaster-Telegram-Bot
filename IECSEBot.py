import os
import requests
import pytz

from datetime import datetime
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
db = SQLAlchemy(app)
ACCESS_TOKEN = str(os.environ.get('ACCESS_TOKEN'))
BASE_URL = 'https://api.telegram.org/bot' + ACCESS_TOKEN
BOARD_ID = str(os.environ.get('BOARD_ID'))


class Event(db.Model):
    name = db.Column(db.VARCHAR, primary_key=True)
    description = db.Column(db.VARCHAR)
    date = db.Column(db.DATE, primary_key=True)
    time = db.Column(db.TIME)
    venue = db.Column(db.VARCHAR)

    def __init__(self, name, description, date, time, venue):
        self.name = name
        self.description = description
        self.date = datetime.strptime(date, '%d/%m/%Y')
        self.time = time
        self.venue = venue

    def __repr__(self):
        return '<Event %r %r %r>' % (self.name, self.date, self.time)


@app.route('/bot', methods=['POST'])
def run_bot():
    try:
        if request.args.get('ACCESS_TOKEN') != ACCESS_TOKEN:
            return jsonify({}), 200

        text = request.json['message']['text']
        chat_id = request.json['message']['chat']['id']
        command = text[1:].split('@')[0]

        if 'create' in command:
            message = create(chat_id, command)
        else:
            options = {'start': start, 'help': bot_help, 'schedule': schedule, 'upcoming': upcoming}
            message = options[command]()

        data = {'chat_id': chat_id, 'text': message}
        if command != 'start':
            data['parse_mode'] = 'markdown'

        requests.post(BASE_URL + '/sendMessage', data=data)
        return jsonify({}), 200

    except Exception as e:
        app.logger.error(repr(e))
        return jsonify({}), 200


def start():
    return 'Hi! @IECSE_Bot keeps you updated about IECSE events.\n\nUse /help to get a list of available commands.'


def bot_help():
    return '- Use /schedule to get a list of all upcoming events.\n- Use /upcoming to get the next event.'


def upcoming():
    cur_datetime = datetime.now(pytz.timezone('Asia/Kolkata'))
    cur_date = cur_datetime.date()
    cur_time = cur_datetime.time()
    event = Event.query.filter(
        (Event.date > cur_date) | ((Event.date == cur_date) & (Event.time >= cur_time))).order_by(Event.date,
                                                                                                  Event.time).first()

    if event is not None:
        return 'Upcoming Event:\n\n*' + event.name + '*\n' + event.description + '\n\n' + event.date.strftime(
            '%A, %B %d, %Y') + '\n' + event.time.strftime('%-I:%M %p') + '\n' + event.venue
    else:
        return 'Sorry, there are no upcoming events.'


def schedule():
    cur_datetime = datetime.now(pytz.timezone('Asia/Kolkata'))
    cur_date = cur_datetime.date()
    cur_time = cur_datetime.time()
    events = Event.query.filter(
        (Event.date > cur_date) | ((Event.date == cur_date) & (Event.time >= cur_time))).order_by(Event.date,
                                                                                                  Event.time).all()

    if len(events) != 0:
        response = 'Schedule:'
        for event in events:
            response += '\n\n*' + event.name + '*\n' + event.description + '\n\n' + event.date.strftime(
                '%A, %B %d, %Y') + '\n' + event.time.strftime('%-I:%M %p') + '\n' + event.venue
        return response
    else:
        return 'Sorry, there are no upcoming events.'


def create(chat_id, command):
    if str(chat_id) != BOARD_ID:
        return 'Sorry, you don\'t have authorization for this action.'
    else:
        command = command.split(' | ')
        if len(command) == 1:
            return 'Create an event by using the /create command in this format:\n\n' + \
                   '/create | name | description | date | time | venue\n\n*name*\nEvent name\n\n' + \
                   '*description*\nEvent description\n\n*date*\nEvent date in dd/MM/yyyy\n\n' + \
                   '*time*\nEvent time in hh:mm am/pm\n\n*venue*\nEvent venue'
        else:
            try:
                event_date = datetime.strptime(command[3], '%d/%m/%Y').date()
                event_time = datetime.strptime(command[4], '%I:%M %p').time()
                cur_datetime = datetime.now(pytz.timezone('Asia/Kolkata'))
                cur_date = cur_datetime.date()
                cur_time = cur_datetime.time()
                if (event_date < cur_date) | ((event_date == cur_date) & (event_time < cur_time)):
                    return 'Sorry, I wish I was The Flash, so I could have messed with the timeline.\n' + \
                           'Please specify a date that\'s not in the past.'

                event = Event(command[1], command[2], command[3], command[4], command[5])
                db.session.add(event)
                db.session.commit()
                return 'Event created successfully.'
            except Exception as e:
                app.logger.error(repr(e))
                return 'Insufficient or invalid arguments passed with /create command.\n\n' + \
                       'Use /create to know how to pass arguments.'


# API code below
@app.route('/events/create/', methods=['POST'])
@app.route('/events/create', methods=['POST'])
def create_event():
    creq = request.json
    try:
        event = Event(creq['eventName'], creq['eventDesc'], creq['date'], creq['time'], creq['venue'])
    except Exception as e:
        app.logger.error(repr(e))
        return jsonify({'success': False, 'message': 'Error, bad request'}), 400
    else:
        try:
            db.session.add(event)
            db.session.commit()
            return jsonify({'success': True, 'message': 'Success'}), 200
        except Exception as e:
            app.logger.error(repr(e))
            return jsonify({'success': False, 'message': 'Error creating event.'}), 400


@app.route('/events/', methods=['GET'])
@app.route('/events', methods=['GET'])
def get_events():
    events = Event.query.all()
    events_list = []
    for event in events:
        events_list.append(
            {'eventName': event.name, 'eventDesc': event.description, 'date': str(event.date),
             'time': str(event.time), 'venue': event.venue})
    return jsonify({'schedule': events_list}), 200


@app.route('/events/edit/', methods=['PUT'])
@app.route('/events/edit', methods=['PUT'])
def edit_event():
    ereq = request.json
    try:
        event = Event.query.filter_by(name=ereq['eventName'], date=ereq['date']).first()
        if event is None:
            return jsonify({'success': False, 'message': 'Event not found'}), 400

        event.description = ereq['eventDesc']
        event.time = ereq['time']
        event.venue = ereq['venue']
        db.session.commit()
        return jsonify({'success': True, 'message': 'Success'}), 200

    except Exception as e:
        app.logger.error(repr(e))
        return jsonify({'success': False, 'message': 'Error, bad request'}), 400


@app.route('/events/remove/', methods=['DELETE'])
@app.route('/events/remove', methods=['DELETE'])
def del_event():
    try:
        event = Event.query.filter_by(name=request.args.get('eventName'), date=request.args.get('date')).first()
        if event is None:
            return jsonify({'success': False, 'message': 'Event not found'}), 400

        db.session.delete(event)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Success'}), 200

    except Exception as e:
        app.logger.error(repr(e))
        return jsonify({'success': False, 'message': 'Error, bad request'}), 400


if __name__ == '__main__':
    app.run()
