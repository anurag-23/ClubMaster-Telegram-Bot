from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://anurag:anurag1849@localhost/anurag'
db = SQLAlchemy(app)


class Event(db.Model):
    name = db.Column(db.VARCHAR, primary_key=True)
    description = db.Column(db.VARCHAR)
    date = db.Column(db.DATE, primary_key=True)
    time = db.Column(db.TIME)
    venue = db.Column(db.VARCHAR)

    def __init__(self, name, description, date, time, venue):
        self.name = name
        self.description = description
        self.date = date
        self.time = time
        self.venue = venue

    def __repr__(self):
        return '<Event %r %r %r>' % (self.name, self.date, self.time)


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
            return jsonify({'success': False, 'message': 'Event already exists'}), 400


@app.route('/events', methods=['GET'])
def get_events():
    events = Event.query.all()
    events_list = []
    for event in events:
        events_list.append(
            {'eventName': event.name, 'eventDesc': event.description, 'date': str(event.date), 'time': str(event.time),
             'venue': event.venue})
    return jsonify({'schedule': events_list}), 200


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


@app.route('/events/remove', methods=['DELETE'])
def del_event():
    try:
        event = Event.query.filter_by(name=request.args.get('name'), date=request.args.get('date')).first()
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
