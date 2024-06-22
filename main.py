from flask import Flask, render_template, url_for, request, redirect, flash
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Integer, String, Text
import datetime
from sqlalchemy_utils.functions import database_exists
from flask_login import LoginManager, UserMixin, login_user, current_user, login_required, logout_user
from wtforms.validators import DataRequired
import requests
from flask_bootstrap import Bootstrap5
from werkzeug.wrappers import Response
from werkzeug.exceptions import HTTPException




login_manager = LoginManager()
app = Flask(__name__)
login_manager.init_app(app)
app.secret_key = 'giga_uga_secret_key'
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///users_notes.db"
db = SQLAlchemy(app)
bootstrap = Bootstrap5(app)


@login_manager.user_loader
def load_user(user_id):
        result = db.session.execute(db.select(User).where(User.id == user_id))
        user = result.scalar()
        if user:
            return user
        else:
            return None

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(unique=True)
    password: Mapped[str] = mapped_column(nullable=False)
    notes = relationship("Note", back_populates="belongs")

"""
    @login_manager.user_loader
    def load_user(self):
        self.id = user_id
        try:
            user = db.session.execute(db.select(User).where(User.id==user_id))
            if user:
                return user
        except:
            return None

"""
class Note(db.Model):
    __tablename__ = 'Notes'
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, db.ForeignKey("users.id"))
    #here already set date as datetime object reverse input from string to date time at post reqauest to add_new
    Date: Mapped[str] = mapped_column(String)
    belongs = relationship("User", back_populates= "notes")
    Description: Mapped[str] = mapped_column(String(250), nullable=False)

###  only on first run
class Loginform(FlaskForm):
    username = StringField(label='Username')
    password = PasswordField(label='Password')
    send = SubmitField(label='login')

class Registerform(Loginform):
    send = SubmitField(label='register')



class addform(FlaskForm):
    ev_date = StringField('date', validators=[DataRequired()])
    description = StringField('description', validators=[DataRequired()])
    send = SubmitField(label='send')


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home'))


@app.route('/')
def home():
    return render_template('index.html', user=current_user)


@app.route('/register', methods=['GET', 'POST'])
def register():
    log_form =Registerform()
    if request.method == 'POST':
        new_user = User(username=log_form.username.data, password=log_form.password.data)
        db.session.add(new_user)
        db.session.commit()
    return render_template('register.html', form=log_form, user=current_user)


###### then work on login
####### then make url for /user/<user.id> and render notes inside divs with some nice touch.
@app.route('/login', methods=['GET', 'POST'])
def login():
    log_form = Loginform()
    if request.method == 'POST':
            t_username = log_form.username.data
            t_password = log_form.password.data
            c_quer = db.session.execute(db.select(User).where(User.username == t_username))
            result = c_quer.scalar()
            if result:
                if result.password == t_password:
                    login_user(result)
                    flash('Logged in successfully.')
                    return redirect(url_for('login'))
                else:
                    flash('wrong login data')
                    return redirect(url_for('login'))
            else:
                flash('No such User. Please supply correct username')

    return render_template('login.html',form=log_form, user=current_user)




@app.route('/users/<string:username>', methods=['GET'])
@login_required
def user_panel(username):
    db_query = db.session.execute(db.select(User).where(User.username == username))
    user_data = db_query.scalar()
    note_list = user_data.notes
    return render_template('user_panel.html', notes=note_list, logged_in=current_user.is_authenticated, user=user_data,
                           username=current_user.username)

@app.route('/user/')
@login_required
def failed_login():
    pass


@app.route('/user/editlist/<string:username>')
@login_required
def editlist(username):
    notes = db.session.execute(db.select(Note).where(Note.belongs == current_user))
    notes_list = notes.scalars().all()
    return render_template('editlist.html', notes=notes_list, username=current_user.username, user=current_user)

@app.route('/user//delete_list/<string:username>')
def delete_list(username):
    notes = db.session.execute(db.select(Note).where(Note.belongs == current_user))
    notes_list = notes.scalars()
    return render_template('delete_list.html', username=current_user.username, notes=notes_list, user=current_user)

##### add new note
@app.route('/add', methods=['GET' ,'POST'])
@login_required
def add():
    form = addform()
    if request.method == 'POST':
        new_note = Note(
            Date=form.ev_date.data,
            belongs=current_user,
            Description=form.description.data
        )
        db.session.add(new_note)
        db.session.commit()

    return render_template('add.html', logged_in=current_user.is_authenticated, user=current_user, form=form)

##update_note
@app.route('/user/<string:username>/edit/<int:noteid>', methods=['GET','POST'])
@login_required
def edit_note(username, noteid):
    note = db.get_or_404(Note,noteid)
    edit_form = addform(
        ev_date = note.Date,
        description=note.Description)
    if edit_form.validate_on_submit():
        note.Date = edit_form.ev_date.data
        note.Description = edit_form.description.data
        db.session.commit()
        return redirect(url_for("user_panel", username=current_user.username))
    return render_template('edit.html', form=edit_form, user=current_user, noteid=noteid)



@app.route('/user/<string:username>/delete/<int:noteid>')
@login_required
def delete_note(username, noteid):
    user = current_user
    notes_list = user.notes
    result_note = db.get_or_404(Note, noteid)
    if result_note in notes_list:
        db.session.delete(result_note)
        db.session.commit()
    return redirect(url_for('user_panel', username=current_user.username))

@app.route('/user/<string:username>/<int:noteid>')
@login_required
def show_note(username,noteid):
    user = current_user
    notes_list = user.notes
    result_note = db.get_or_404(Note, noteid)
    if result_note in notes_list:
        return render_template('note.html', user=current_user, note=result_note)
    else:
        return  HTTPException(description='No such note for current user', response=Response(status=404))



if __name__ == '__main__':
    app.run(debug=True)


###### at the end make api restful