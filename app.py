from flask import Flask, render_template, request, redirect, url_for, send_file, jsonify
from pymongo import MongoClient
from cassandra.cluster import Cluster
from uuid import uuid4, UUID
from collections import defaultdict
import matplotlib
matplotlib.use('Agg')  # Use the 'Agg' backend which doesn't require a display
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import io
import os
from dotenv import load_dotenv

app = Flask(__name__)
load_dotenv()
MONGO_URI = os.getenv('MONGO_URI')
# Connect to MongoDB Atlas
client = MongoClient(MONGO_URI)
db = client.todo
tasks_collection = db.tasks

# Connect to Cassandra
cluster = Cluster(['127.0.0.1'])  # Replace '127.0.0.1' with your Cassandra node IP
session = cluster.connect()
session.execute("CREATE KEYSPACE IF NOT EXISTS todo WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1}")
session.set_keyspace('todo')
session.execute("CREATE TABLE IF NOT EXISTS tasks (id UUID PRIMARY KEY, task TEXT, group_tag TEXT, day TEXT, hour TEXT)")

# Ensure each request has its own Matplotlib instance
def create_plot():
    fig, ax = plt.subplots()
    return fig, ax

def save_plot(fig):
    img_bytes = io.BytesIO()
    fig.savefig(img_bytes, format='png')
    img_bytes.seek(0)
    plt.close(fig)
    return img_bytes

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/input_tasks')
def input_tasks():
    return render_template('input_tasks.html')

@app.route('/show_analysis')
def show_analysis():
    return render_template('show_analysis.html')

@app.route('/add', methods=['POST'])
def add():
    task = request.form['task']
    group_tag = request.form['group']
    day = request.form.get('day')
    hour = request.form.get('hour')

    if task != "":
        if group_tag == "":
            group_tag = "default"

        task_id = str(uuid4())
        task_uuid = UUID(task_id)

        # Insert task into MongoDB
        tasks_collection.insert_one({
            '_id': task_id,
            'task': task,
            'group_tag': group_tag,
            'day': day,
            'hour': hour
        })

        # Insert task into Cassandra
        session.execute("INSERT INTO tasks (id, task, group_tag, day, hour) VALUES (%s, %s, %s, %s, %s)",
                        (task_uuid, task, group_tag, day, hour))

    return redirect(url_for('index'))

@app.route('/delete/<id>', methods=['POST'])
def delete_task(id):
    # Delete task from MongoDB
    tasks_collection.delete_one({'_id': id})
    
    # Convert the id to a UUID object
    task_uuid = UUID(id)

    # Delete task from Cassandra
    session.execute("DELETE FROM tasks WHERE id = %s", [task_uuid])
    return jsonify({'status': 'success'})

@app.route('/tasks_count_chart')
def tasks_count_chart():
    rows = tasks_collection.find()
    task_counts = defaultdict(int)
    for row in rows:
        task_counts[row['group_tag']] += 1

    # Create a pie chart
    labels = list(task_counts.keys())
    sizes = list(task_counts.values())
    fig, ax = create_plot()
    ax.pie(sizes, labels=labels, autopct='%1.1f%%')
    ax.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle

    # Save the plot to a BytesIO object
    img_bytes = save_plot(fig)

    # Send the image as a file
    return send_file(img_bytes, mimetype='image/png')

@app.route('/task_histogram')
def task_histogram():
    rows = tasks_collection.find()
    task_counts = defaultdict(int)
    for row in rows:
        task_counts[row['group_tag']] += 1

    # Create a histogram
    labels = list(task_counts.keys())
    sizes = list(task_counts.values())
    fig, ax = create_plot()
    ax.bar(labels, sizes)
    ax.set_xlabel('Group')
    ax.set_ylabel('Number of Tasks')
    ax.set_title('Number of Tasks in Each Group')

    ax.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))

    # Save the histogram to a BytesIO object
    img_bytes = save_plot(fig)

    # Send the histogram image as a file
    return send_file(img_bytes, mimetype='image/png')

@app.route('/task_hour')
def task_hour():
    rows = tasks_collection.find()
    task_counts = defaultdict(int)

    for row in rows:
        # Extract hour from the 'hour' field (assuming hour is stored in 'hour:minute' format)
        hour = row['hour'].split(':')[0]
        task_counts[hour] += 1

    # Create a histogram
    hours = list(task_counts.keys())
    tasks = list(task_counts.values())

    # Convert hours to integers for proper sorting and plotting
    hours_int = [int(hour) for hour in hours]
    hours_sorted, tasks_sorted = zip(*sorted(zip(hours_int, tasks)))

    fig, ax = create_plot()
    ax.bar(hours_sorted, tasks_sorted)
    ax.set_xlabel('Hour of the Day')
    ax.set_ylabel('Number of Tasks')
    ax.set_title('Number of Tasks by Hour of the Day')

    # Set x-axis ticks to show every hour
    ax.xaxis.set_major_locator(ticker.MultipleLocator(1))

    # Ensure integers are displayed for hours on x-axis
    ax.xaxis.set_major_formatter(ticker.FormatStrFormatter('%d'))

    # Set the x-axis limit from 0 to 23 (assuming 24-hour format)
    ax.set_xlim(0, 23)

    # Save the histogram to a BytesIO object
    img_bytes = save_plot(fig)

    # Send the histogram image as a file
    return send_file(img_bytes, mimetype='image/png')

@app.route('/task_month')
def task_month():
    rows = tasks_collection.find()
    task_counts = defaultdict(int)

    for row in rows:
        # Extract month from the 'day' field (assuming day is stored in 'YYYY-MM-DD' format)
        month = row['day'].split('-')[1]
        task_counts[month] += 1

    # Create a histogram
    months = list(task_counts.keys())
    tasks = list(task_counts.values())

    # Convert months to integers for proper sorting and plotting
    months_int = [int(month) for month in months]
    months_sorted, tasks_sorted = zip(*sorted(zip(months_int, tasks)))

    fig, ax = create_plot()
    ax.bar(months_sorted, tasks_sorted)
    ax.set_xlabel('Month')
    ax.set_ylabel('Number of Tasks')
    ax.set_title('Number of Tasks by Month')

    # Set x-axis ticks to show every month
    ax.xaxis.set_major_locator(ticker.MultipleLocator(1))

    # Ensure integers are displayed for months on x-axis
    ax.xaxis.set_major_formatter(ticker.FormatStrFormatter('%d'))

    # Save the histogram to a BytesIO object
    img_bytes = save_plot(fig)

    # Send the histogram image as a file
    return send_file(img_bytes, mimetype='image/png')

@app.route('/show_all_tasks')
def show_all_tasks():
    # Fetch all tasks from the database
    rows = tasks_collection.find()
    tasks = [{'id': str(row['_id']), 'task': row['task'], 'group': row['group_tag'], 'time': row['hour'], 'day': row['day']} for row in rows]

    return jsonify(tasks)

if __name__ == '__main__':
    app.run(debug=True)
