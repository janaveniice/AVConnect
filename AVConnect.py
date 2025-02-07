from bson import ObjectId, errors as bson_errors
from difflib import get_close_matches
from flask import (
    Flask,
    json,
    jsonify,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session
)
from flask_pymongo import PyMongo
from pymongo import MongoClient
from datetime import datetime, timedelta
import logging

app = Flask(__name__)
app.secret_key = "avconnect"  # Replace with a secure string

# Database configuration
app.config[
    "MONGO_URI"
] = "mongodb://localhost:27017/AVConnection"  # if required, modify the port no.
mongo = PyMongo(app)
client = MongoClient(app.config["MONGO_URI"])
db = client["AVConnection"]

# ======================================= creating and inserting to db =========================================
# Collection names 
collections = {
    "maintenances": db["Maintenances"],
    "users": db["Users"],
    "threads": db["DiscussionThreads"],
    "dashboard": db["Dashboards"],
    "replies": db["Replies"],
    "records": db["Records"],
    "resources": db["Resources"],
}

# Configure logging
logging.basicConfig(level=logging.INFO)

# Load data from a JSON file
def load_data(file_path):
    try:
        with open(file_path) as json_file:
            return json.load(json_file)
    except FileNotFoundError:
        logging.error("data.json file not found.")
        return None
    except json.JSONDecodeError:
        logging.error("Error decoding JSON.")
        return None


# Prepare resources data by adding a unique number to resourceName and url fields.
def prepare_resources_data(data_list):
    for i, item in enumerate(data_list, start=1):
        item["resourceName"] = f"{item['resourceName']}{i}"
        item["url"] = f"{item['url']}/{i}"
        if "_id" not in item:
            item["_id"] = ObjectId()

    # Adding 5 additional resources
    for i in range(len(data_list) + 1, len(data_list) + 5):
        new_resource = {
            "_id": ObjectId(),
            "resourceName": f"Resource {i}",
            "url": f"http://example.com/resource/{i}",
        }
        data_list.append(new_resource)

    return data_list


# Prepare replies data by ensuring each item has a valid _id.
def prepare_replies_data(data_list):
    for item in data_list:
        if "_id" not in item:
            item["_id"] = ObjectId()
    return data_list


# Insert data into the specified collection.
def insert_data(collection, data):
    if collection.estimated_document_count() == 0:
        for item in data:
            try:
                item["_id"] = (
                    ObjectId(item["_id"])
                    if isinstance(item["_id"], str)
                    else item["_id"]
                )
                if "user_id" in item:
                    item["user_id"] = (
                        ObjectId(item["user_id"])
                        if isinstance(item["user_id"], str)
                        else item["user_id"]
                    )

                collection.insert_one(item)
                logging.info(f"Inserted item into {collection.name}: {item}")
            except bson_errors.InvalidId:
                logging.error(f"Invalid ObjectId for item: {item}. Skipping.")
            except Exception as e:
                logging.error(f"Error inserting item into {collection.name}: {e}")
    else:
        logging.info(f"{collection.name} already contains data. Skipping insertion.")


# Load and insert data from JSON file
data = load_data("data.json")
if data:
    # Prepare resources and replies data
    data["resources"] = prepare_resources_data(data["resources"])
    data["replies"] = prepare_replies_data(data["replies"])

    insert_data(collections["users"], data["users"])
    insert_data(collections["maintenances"], data["maintenances"])
    insert_data(collections["dashboard"], data["dashboard"])
    insert_data(collections["threads"], data["discussion_threads"])
    insert_data(collections["replies"], data["replies"])
    insert_data(collections["resources"], data["resources"])

    logging.info("All data imported successfully.")

# ============================================ END =============================================================

# ========================================== Login =============================================================
@app.route("/", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        # Retrieve user information. Not using hashlib for simplicity
        user = collections["users"].find_one({"username": username, "password": password})

        if user:
            # Store string _id into session
            session["user_id"] = str(user["_id"])
            # print(session.get("user_id"))
            return redirect(url_for("dashboard"))
        else:
            error = "Invalid username or password"

        if error:
            return render_template("authentication.html", error=error)
    return render_template("authentication.html")

# ========================================== Login =============================================================
@app.route("/register", methods=["GET", "POST"])
def register():
    error = None
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        # Check if username is taken
        existing_user = collections["users"].find_one({"username": username})
        if existing_user:
            error = "Username already taken, please choose another"

        # Check if passwords match
        elif password != confirm_password:
            error = "Passwords do not match"

        if error:
            return render_template("register.html", error=error)

        # Create new user object
        new_user = {
            "username": username,
            "password": password
        }
        collections["users"].insert_one(new_user)

        return redirect(url_for("login"))

    return render_template("register.html", error=error)

# ========================================== DASHBOARD =============================================================
# Main dashboard
@app.route("/dashboard")
def dashboard():
    # Retrieve user_id from session (uncomment this in production)
    user_id = ObjectId(session.get("user_id"))
    user = collections["users"].find_one({"_id": user_id})
    if user_id is None:
        return redirect(url_for('login'))  # Redirect to login if user_id is not found

    # Example user ID for testing; replace this with session retrieval in production.
    # user_id = ObjectId("60d5f9e2b7f2c8e7e74f6b80")
    dashboard_data = collections["dashboard"].find_one({"user_id": user_id})

    # Retrieve and sort maintenance reminders by date
    maintenance_reminders = (
        collections["maintenances"].find({"user_id": user_id}).sort("date", 1)
    )

    # Format dates and filter for weekdays only
    formatted_reminders = []
    for reminder in maintenance_reminders:
        date_str = reminder["date"]
        date_obj = datetime.fromisoformat(date_str)
        if date_obj.weekday() < 5:  # Only keep weekdays
            if date_obj >= datetime.now():
                formatted_date = date_obj.strftime("%d %b")  # Format to DD MMMM YYYY
                reminder["formatted_date"] = formatted_date
                if "title" in reminder:
                    formatted_reminders.append(reminder)

    return render_template(
        "dashboard/dashboard.html",
        dashboard=dashboard_data,
        maintenance_reminders=formatted_reminders, user=user
    )

# Update AV Settings
@app.route("/update_settings", methods=["POST"])
def update_settings():
    battery = request.form.get("battery")
    tire_pressure = request.form.get("tirePressure")
    user_id = ObjectId(session.get("user_id"))
    # user_id = ObjectId("60d5f9e2b7f2c8e7e74f6b80")  # Example user ID

    # Check if the user has an existing dashboard entry
    existing_dashboard = collections["dashboard"].find_one({"user_id": user_id})
    if existing_dashboard:
        result = collections["dashboard"].update_one(
            {"user_id": user_id},
            {"$set": {"battery": f"{battery}%", "tirePressure": f"{tire_pressure} psi"}},
        )
        if result.modified_count > 0:
            flash("Settings updated successfully!", "success")
        else:
            flash("No changes were made; the settings were already up to date.", "info")
    else:
        # Insert a new entry for new users
        collections["dashboard"].insert_one({
            "user_id": user_id,
            "battery": f"{battery}%",
            "tirePressure": f"{tire_pressure} psi",
        })
        flash("Settings saved for the first time.", "success")

    return redirect(url_for("dashboard"))


# View all reminders
@app.route("/reminders")
def view_reminders():
    user_id = ObjectId(session.get("user_id"))
    user = collections["users"].find_one({"_id": user_id})
    # user_id = ObjectId("60d5f9e2b7f2c8e7e74f6b80")  # Replace with the current user's ID
    maintenance_reminders = list(collections["maintenances"].find({"user_id": user_id}))

    # Format the date for display and add datetime object for sorting
    for reminder in maintenance_reminders:
        reminder["formatted_date"] = datetime.fromisoformat(reminder["date"]).strftime(
            "%d %B %Y %I:%M %p"
        )
        reminder["date_obj"] = datetime.fromisoformat(
            reminder["date"]
        )  # Add a datetime object for comparison

    # Separate into past and future reminders
    past_reminders = [
        reminder
        for reminder in maintenance_reminders
        if reminder["date_obj"] < datetime.now()
    ]
    future_reminders = [
        reminder
        for reminder in maintenance_reminders
        if reminder["date_obj"] >= datetime.now()
    ]

    # Sort both past and future reminders by date
    past_reminders.sort(key=lambda x: x["date_obj"])
    future_reminders.sort(key=lambda x: x["date_obj"])

    return render_template(
        "dashboard/dashboard.html",
        future_reminders=future_reminders,
        past_reminders=past_reminders, user=user
    )


# View all reminders
@app.route("/allreminders")
def view_all_reminders():
    user_id = ObjectId(session.get("user_id"))
    user = collections["users"].find_one({"_id": user_id})
    # user_id = ObjectId("60d5f9e2b7f2c8e7e74f6b80")  # Replace with the current user's ID
    maintenance_reminders = list(collections["maintenances"].find({"user_id": user_id}))

    # Format the date for display and add datetime object for sorting
    for reminder in maintenance_reminders:
        reminder["formatted_date"] = datetime.fromisoformat(reminder["date"]).strftime(
            "%d %B %Y %I:%M %p"
        )
        reminder["date_obj"] = datetime.fromisoformat(
            reminder["date"]
        )  # Add a datetime object for comparison

    # Separate into past and future reminders
    past_reminders = [
        reminder
        for reminder in maintenance_reminders
        if reminder["date_obj"] < datetime.now()
    ]
    future_reminders = [
        reminder
        for reminder in maintenance_reminders
        if reminder["date_obj"] >= datetime.now()
    ]

    # Sort both past and future reminders by date
    past_reminders.sort(key=lambda x: x["date_obj"])
    future_reminders.sort(key=lambda x: x["date_obj"])

    return render_template(
        "dashboard/reminders.html",
        future_reminders=future_reminders,
        past_reminders=past_reminders, user=user
    )


# Add reminders
@app.route("/add_reminder", methods=["POST"])
def add_reminder():
    title = request.form.get("title")
    description = request.form.get("description")
    date_str = request.form.get("date")
    location = request.form.get("location")  # Get the location from the form
    user_id = ObjectId(session.get("user_id"))
    # user_id = ObjectId("60d5f9e2b7f2c8e7e74f6b80")  # Replace with the current user's ID

    # Parse the date and check if it's in the future
    date_obj = datetime.fromisoformat(date_str)
    current_date = datetime.now()

    # Ensure the date is in the future
    if date_obj <= current_date:
        flash("Please select a date and time later than today.", "warning")
        return redirect(url_for("dashboard"))

    # Additional checks for weekdays and office hours
    if date_obj.weekday() >= 5:  # 5 = Saturday, 6 = Sunday
        flash("Reminders can only be added on weekdays.", "warning")
        return redirect(url_for("dashboard"))

    if not (9 <= date_obj.hour < 17):  # Check if time is between 9 AM and 5 PM
        flash("Reminders can only be set between 9 AM and 5 PM.", "warning")
        return redirect(url_for("dashboard"))

    # Add the reminder to the user's reminders list
    collections["maintenances"].insert_one(
        {
            "user_id": user_id,
            "title": title,
            "description": description,
            "date": date_str,
            "location": location,  # Save the location
        }
    )

    flash("Maintenance reminder added successfully!", "success")
    return redirect(url_for("dashboard"))


# Edit Reminder
@app.route("/edit_reminder/<reminder_id>", methods=["POST"])
def edit_reminder(reminder_id):
    title = request.form.get("title")
    description = request.form.get("description")
    date_str = request.form.get("date")
    location = request.form.get("location")
    date_obj = datetime.fromisoformat(date_str)
    current_date = datetime.now()

    # Validation for future dates, weekdays, and office hours
    if date_obj <= current_date:
        flash("Please select a date and time later than today.", "warning")
        return redirect(url_for("view_reminders"))

    if date_obj.weekday() >= 5:
        flash("Reminders can only be added on weekdays.", "warning")
        return redirect(url_for("view_reminders"))

    if not (9 <= date_obj.hour < 17):
        flash("Reminders can only be set between 9 AM and 5 PM.", "warning")
        return redirect(url_for("view_reminders"))

    # Update the reminder in the database
    collections["maintenances"].update_one(
        {"_id": ObjectId(reminder_id)},
        {
            "$set": {
                "title": title,
                "description": description,
                "date": date_str,
                "location": location,
            }
        },
    )
    flash("Reminder updated successfully!", "success")
    return redirect(url_for("dashboard"))


# Delete Reminder
@app.route("/delete_reminder/<reminder_id>", methods=["POST"])
def delete_reminder(reminder_id):
    # Your logic to delete the reminder
    collections["maintenances"].delete_one({"_id": ObjectId(reminder_id)})
    flash("Reminder deleted successfully!", "success")
    return redirect(url_for("dashboard"))

# ============================================================= Forum =============================================================

@app.template_filter('datetimeformat')
def datetimeformat(value):
    # Check if value is already a datetime object
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")

    # If it's a string, attempt to parse it into a datetime object
    try:
        parsed_date = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed_date.strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        # Return the value unchanged if it can't be parsed
        return value


# @app.template_filter('datetimeformat')
# def datetimeformat(value):
#     if 'T' in value or 'Z' in value:
#         timestamp_obj = datetime.strptime(value, '%Y-%m-%dT%H:%M:%SZ')
#     else:
#         timestamp_obj = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
#     return timestamp_obj.strftime('%Y/%m/%d %I:%M%p').lower()

@app.route("/forum")
def forum():
    user_id = ObjectId(session.get("user_id"))
    user = collections["users"].find_one({"_id": user_id})
    search_query = request.args.get('search', '')
    
    if search_query:
        # Filter forum posts based on the search query
        forum_posts = list(collections["threads"].find({
            "$or": [
                {"subject": {"$regex": search_query, "$options": "i"}},
                {"content": {"$regex": search_query, "$options": "i"}}
            ]
        }))
    else:
        # Fetch all forum posts if no search query
        forum_posts = list(collections["threads"].find())
        
    # Fetch user details and count replies for each post
    for post in forum_posts:
        postuser = collections["users"].find_one(
            {"_id": ObjectId(post["user_id"])}
        )  # Assuming you have a users collection

        # Adding user information
        if postuser:
            post["user"] = {
                "id": str(postuser["_id"]),
                "username": postuser.get(
                    "username", "Unknown User"
                ),  
            }
        else:
            post["user"] = {
                "id": str(post["user_id"]),
                "username": "Unknown User",  # Fallback if user not found
            }

        # Count replies related to this thread
        post["replies"] = collections["replies"].count_documents(
            {"thread_id": str(post["_id"])}
        )

    print("forum_posts: ", forum_posts)
    return render_template("forum/mainForum.html", posts=forum_posts, user=user)

@app.route("/new_thread")
def new_thread():
    user_id = ObjectId(session.get("user_id"))
    user = collections["users"].find_one({"_id": user_id})
    return render_template("forum/newThread.html", user=user)

@app.route("/thread/<id>", methods=["GET", "POST"])
def one_thread(id):
    try:
        thread_id = ObjectId(id)  # Convert to ObjectId
        logging.info(f"Fetching thread with ID: {thread_id}")
    except Exception as e:
        logging.error(f"Error converting thread ID: {e}")
        return "Invalid thread ID format", 400

    # Get data from 'threads' collection
    thread = collections["threads"].find_one({"_id": thread_id})
    if thread is None:
        logging.warning(f"Thread not found for ID: {thread_id}")
        return "Thread not found", 404

    # Get user info based on user_id
    user_id = ObjectId(session.get("user_id"))
    user = collections["users"].find_one({"_id": user_id})
    threaduser = collections["users"].find_one({"_id": ObjectId(thread["user_id"])})
    if threaduser is None:
        logging.warning(f"User not found for user_id: {thread['user_id']}")
        return "User not found", 404

    # Get replies related to this thread
    replies = list(collections["replies"].find({"thread_id": str(thread_id)}))
    logging.info(f"Replies for thread ID {thread_id}: {replies}")

    # Prepare replies with usernames and format timestamps
    enriched_replies = []
    for reply in replies:
        reply_user = collections["users"].find_one({"_id": ObjectId(reply["user_id"])})
        reply["username"] = reply_user["username"] if reply_user else "Unknown User"

        # Convert timestamp from ISO 8601 format
        if isinstance(reply.get("timestamp"), str):
            reply["timestamp"] = datetime.fromisoformat(reply["timestamp"])
        reply["formatted_timestamp"] = reply["timestamp"].strftime('%Y-%m-%d %H:%M:%S') if reply.get("timestamp") else "N/A"

        enriched_replies.append(reply)

    # Get sort parameter from the request
    sort_by = request.args.get("sort", "recent")
    filter_timestamp_str = request.args.get("filter_timestamp")  # Get the filter timestamp from the request

    # If a filter timestamp is provided, convert it to a datetime object
    if filter_timestamp_str:
        try:
            filter_timestamp = datetime.fromisoformat(filter_timestamp_str)
            # Filter replies based on the timestamp
            enriched_replies = [
                reply for reply in enriched_replies
                if reply["timestamp"] >= filter_timestamp  
            ]
        except ValueError:
            logging.error(f"Invalid filter timestamp format: {filter_timestamp_str}")

    # Sorting logic based on the sort_by parameter
    if sort_by == "popular":
        enriched_replies.sort(key=lambda r: r.get("likes", 0), reverse=True)  
    else:
        enriched_replies.sort(key=lambda r: r["timestamp"], reverse=True)  

    return render_template(
        "forum/thread.html",
        thread=thread,
        replies=enriched_replies,
        username=threaduser["username"],
        user_id=session.get("user_id"),
        user=user
    ) 

@app.route("/thread/<thread_id>/comment", methods=["POST"])
def add_comment(thread_id):
    comment_content = request.form.get("comment-content")
    print("thread_id: ",thread_id)
    
    if comment_content:
        comment = {
          "user_id": ObjectId(session.get("user_id")),

            "thread_id": thread_id,  
            "content": comment_content,
            "timestamp":datetime.now(),
        }
        
        collections["replies"].insert_one(comment)  # Use the correct collection for comments
        flash("Comment added successfully!", "success")  # Flash message for user feedback
    else:
        flash("Comment cannot be empty!", "error")
    
    # Redirect to the thread view
    return one_thread(thread_id);  


@app.route("/submit_thread", methods=["POST"])
def submit_thread():
    data = request.get_json()

    # Validate the received data
    subject = data.get("subject")
    content = data.get("content")
    user_id = ObjectId(session.get("user_id"))  # to be replaces with user session_ID 

    if not subject or not content:
        return (
            jsonify({"success": False, "message": "Subject and content are required"}),
            400,
        )

    # insert data to the database
    new_thread = {
        "user_id": user_id,
        "subject": subject,
        "content": content,
        "timestamp": datetime.now()
    }

    result = collections["threads"].insert_one(new_thread)
    flash("Thread added successfully!", "success")  # Flash message for user feedback


    if result.inserted_id:
        return (
            jsonify({"success": True, "message": "Thread submitted successfully!"}),
            201,
        )
    else:
        return jsonify({"success": False, "message": "Failed to submit thread"}), 500



# ============================================================= Safety =============================================================
@app.route("/safety")
def safety():
    user_id = ObjectId(session.get("user_id"))
    user = collections["users"].find_one({"_id": user_id})
    # Load data from data.json
    with open("data.json") as f:
        data = json.load(f)

    # Extract reports data
    reports = data.get("reports", [])

    return render_template("safety/safetyRecords.html", reports=reports, user=user)


@app.route("/safety-details/<report_id>")
def safety_details(report_id=None):
    user_id = ObjectId(session.get("user_id"))
    user = collections["users"].find_one({"_id": user_id})
    # Load data from data.json
    with open("data.json") as f:
        data = json.load(f)

    # Find the specific report by id
    report = next(
        (r for r in data.get("reports", []) if str(r["id"]) == report_id), None
    )

    return render_template("safety/indvSafetyRecord.html", report=report, user=user)


@app.route("/safety-resources")
def safety_resources():
    user_id = ObjectId(session.get("user_id"))
    user = collections["users"].find_one({"_id": user_id})
    # Retrieve all resources from MongoDB
    resources = list(collections["resources"].find())
    return render_template("safety/safetyResources.html", resources=resources, user=user)


@app.route("/safety-resources-details", methods=["GET", "POST"])
def safety_resources_details():
    user_id = ObjectId(session.get("user_id"))
    user = collections["users"].find_one({"_id": user_id})
    resource_id = request.form.get("resource_id")
    resource = collections["resources"].find_one({"_id": ObjectId(resource_id)})
    return render_template("safety/indvSafetyResource.html", resource=resource, user=user)


# ============================================================= FAQ =============================================================

@app.route("/faq", methods=["GET"])
def faq():
    user_id = ObjectId(session.get("user_id"))
    user = collections["users"].find_one({"_id": user_id})
    faqs = data.get("faqs", [])
    query = request.args.get("query", "").lower()
    
    if query:
        matched_faqs = [faq for faq in faqs if query in faq["question"].lower() or query in faq["answer"].lower()]
        
        if not matched_faqs:

            all_texts = [faq["question"] for faq in faqs] + [faq["answer"] for faq in faqs]
            closest_match = get_close_matches(query, all_texts, n=1, cutoff=0.1)
            suggestion = closest_match[0] if closest_match else None

            return render_template("faq/faq.html", faqs=[], query=query, page=1, total_pages=1, suggestion=suggestion, no_match=True)

    else:
        matched_faqs = faqs

    page = request.args.get("page", 1, type=int)
    per_page = 5
    total_pages = (len(matched_faqs) + per_page - 1) // per_page 
    matched_faqs = matched_faqs[(page - 1) * per_page : page * per_page]  

    return render_template("faq/faq.html", faqs=matched_faqs, query=query, page=page, total_pages=total_pages, no_match=False, user=user)   

# ========================================== Profile =============================================================
@app.route("/profile")
def profile():
    userId = ObjectId(session.get("user_id"))
    #userId = ObjectId('60d5f9e2b7f2c8e7e74f6b83')
    user = collections["users"].find_one({"_id": userId})

    # Retrieve user threads
    threads = list(collections["threads"].find({"user_id": ObjectId(userId)}))

    # Retrieve user replies
    replies = list(collections["replies"].find({"user_id": userId}))
    for reply in replies:
        # Retrieve thread subject for each reply
        thread = collections["threads"].find_one({"_id": ObjectId(reply["thread_id"])})
        reply["thread_subject"] = thread["subject"]

    return render_template("profile/userProfile.html", user=user, threads=threads, replies=replies)

@app.route("/delete-thread/<string:thread_id>", methods=["POST"])
def delete_thread(thread_id):
    collections["threads"].delete_one({"_id": ObjectId(thread_id)})

    flash("Thread deleted successfully!", "success")
    return redirect(url_for("profile"))

@app.route("/delete-comment/<string:reply_id>", methods=["POST"])
def delete_comment(reply_id):
    collections["replies"].delete_one({"_id": ObjectId(reply_id)})

    flash("Comment deleted successfully!", "success")
    return redirect(url_for("profile"))

# ========================================== Logout =============================================================
@app.route("/logout")
def logout():
    session.pop("user_id", None)
    return redirect(url_for("login"))

# ========================================== End =============================================================
if __name__ == "__main__":
    app.run(debug=True)
