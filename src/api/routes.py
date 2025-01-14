"""
This module takes care of starting the API Server, Loading the DB and Adding the endpoints
"""
from flask import Flask, request, jsonify, url_for, Blueprint
from api.utils import generate_sitemap, APIException
from flask_cors import CORS
from datetime import datetime, timezone
from api.models import db, Companies, Users, Administrators, Applications, Histories, Expenses, Employees
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required


api = Blueprint('api', __name__)
CORS(api) 


@api.route("/login", methods=["POST"]) 
def login():
    response_body = {}
    data = request.json
    email = data.get("email", None)
    password = data.get("password", None)
    user = db.session.execute(db.select(Users).where(Users.email == email, Users.password == password, Users.is_active)).scalar()
    if not user:
        response_body["message"]="Bad email or password"
        return response_body, 401
    access_token = create_access_token(identity={'email': user.email, 'user_id': user.id, 'is_app_admin': user.is_app_admin, 'company_id': user.company_id})
    response_body["message"] = f'Bienvenida {email}'
    response_body['results'] = user.serialize()
    response_body['access_token'] = access_token
    return response_body, 200


@api.route("/sign-up", methods=['POST'])
def signup():
    response_body = {}
    data = request.json
    row = Users(email = data.get("email"),
                password = data.get("password"),
                is_active = True,
                is_app_admin = False,
                company_id = 1)

    db.session.add(row)
    db.session.commit()
    response_body['message'] = f'Bienvenido {data.get("email")}'
    response_body['results'] = {}
    return response_body, 200


@api.route('/companies', methods=['GET', 'POST'])
@jwt_required() 
def companies():
    response_body = {}
    current_user = get_jwt_identity()
    user = db.session.get(Users, current_user)
    if not user.is_app_admin:
        response_body['message'] = 'Permiso denegado'
        return response_body, 403
    if request.method == 'GET':
        rows = db.session.execute(db.select(Companies)).scalars()
        if not rows:
            response_body['message'] = 'No hay compañías para mostrar'
            response_body['results'] = []
            return response_body, 404
        result = [row.serialize() for row in rows]
        response_body['message'] = 'Listado de todas las compañías (GET)'
        response_body['results'] = result
        return response_body, 200
    if request.method == 'POST':
        data = request.get_json()
        if not data.get('name'):
            response_body['message'] = 'Faltan datos requeridos'
            return response_body, 400
        row = Companies(name=data.get('name'),
                        date_recored=datetime.now())
        db.session.add(row)
        db.session.commit()
        response_body['message'] = 'Compañía creada exitosamente'
        response_body['results'] = row.serialize()
        return response_body, 201


@api.route('/users', methods=['GET', 'POST'])
@jwt_required()
def users():
    response_body = {}
    current_user = get_jwt_identity()
    user = db.session.get(Users, current_user["user_id"])
    if not user.is_app_admin:
        response_body['message'] = 'Permiso denegado'
        return response_body, 403
    if request.method == 'GET':
        rows = db.session.execute(db.select(Employees)).scalars()
        if not rows:
            response_body['message'] = f'User no existe'
            response_body['result'] = {}
            return response_body, 404
        result = [row.serialize() for row in rows]
        response_body['message'] = 'Listado de todos los users (GET)'
        response_body['results'] = result
        return response_body, 200
    if request.method == 'POST':
        data = request.json()
        row = users(email = data.get('email'),
                    password = data.get('password'),
                    is_active = data.get('is_asctive'),
                    is_app_admin = data.get('is_app_admin'),
                    date = datetime.now(),
                    company_id = data.get('company_id'))
        db.session.add(row)
        db.session.commit()
        response_body['message'] = 'Creando una compañia (POST)'
        response_body['results'] = row.serialize()
        return response_body, 201


@api.route('/administrators', methods=['GET', 'POST'])
@jwt_required()
def administrators():
    response_body = {}
    current_user = get_jwt_identity()
    user = db.session.get(Users, current_user['user_id'])
    if not user:
        return {"message": "Usuario no encontrado"}, 404
    if not user.is_app_admin and not user.is_company_admin:
        return {"message": "Permiso denegado"}, 403
    if request.method == 'GET':
        query = db.select(Administrators).join(Users, Administrators.user_id == Users.id).filter(Users.company_id == user.company_id)
        rows = db.session.execute(query).scalars()
        if not rows:
            return {"message": "No hay empleados en esta compañía", "results": []}, 404
        result = [row.serialize() for row in rows]
        return {"message": "Empleados encontrados", "results": result}, 200
    if request.method == 'POST':
        if user.company_id != 0 and not user.is_company_admin:
            response_body['message'] = 'Permiso denegado para crear administradores'
            return response_body, 403
        data = request.json
        new_user = Users(email=data.get('email'),
                        password=data.get('password'),
                        is_active=True,
                        is_app_admin=False,
                        is_company_admin=True,
                        company_id=user.company_id)
        db.session.add(new_user)
        db.session.commit() 
        row = Administrators(name=data.get('name'),
                             last_name=data.get('last_name'),
                             date_created=datetime.now(),
                             user_id = new_user.id)
        db.session.add(row)
        db.session.commit()
        response_body['message'] = 'Administrador creado exitosamente'
        response_body['results'] = row.serialize()
        return response_body, 201


@api.route('/employees', methods=['GET', 'POST'])
@jwt_required()
def employees():
    response_body = {}
    current_user = get_jwt_identity()
    user = db.session.get(Users, current_user['user_id'])
    if not user:
        return {"message": "Usuario no encontrado"}, 404
    if not user.is_app_admin and not user.is_company_admin: 
        return {"message": "Permiso denegado"}, 403
    if request.method == 'GET':
        query = db.select(Employees).join(Users, Employees.user_id == Users.id).filter(Users.company_id == user.company_id)
        rows = db.session.execute(query).scalars()
        if not rows:
            return {"message": "No hay empleados en esta compañía", "results": []}, 404
        result = [row.serialize() for row in rows]
        return {"message": "Empleados encontrados", "results": result}, 200
    if request.method == 'POST':
        if user.company_id != 0 and not user.is_company_admin:
            response_body['message'] = 'Permiso denegado para crear administradores'
            return response_body, 403
        data = request.json
        new_user = Users(email=data.get('email'),
                        password=data.get('password'),
                        is_active=True,
                        is_app_admin=False,
                        is_company_admin=False,
                        company_id=user.company_id)
        db.session.add(new_user)
        db.session.commit() 
        row = Employees(name=data.get('name'),
                        last_name=data.get('last_name'),
                        date_created=datetime.now(),
                        budget_limit= data.get('budget_limit'),
                        user_id = new_user.id)
        db.session.add(row)
        db.session.commit()
        response_body['message'] = 'Compañía registrada exitosamente'
        response_body['results'] = user.serialize()
        response_body['results']['employee'] = employee.name
        response_body['results']['employeeid'] = employee.id
        return response_body, 201


@api.route('/applications', methods=['GET', 'POST'])
@jwt_required()
def applications():
    response_body = {}
    current_user = get_jwt_identity()
    user = db.session.get(Users, current_user['user_id'])
    if not (user.is_app_admin or user.is_company_admin or user.company_id != 0):
        response_body['message'] = 'Permiso denegado'
        return response_body, 403
    if request.method == 'GET':
        if user.is_app_admin:
            rows = db.session.execute(db.select(Applications)).scalars()
        elif user.is_company_admin:
            company_id = user.company_id
            rows = db.session.execute(
                db.select(Applications)
                .join(Employees, Employees.id == Applications.employee_id)
                .join(Users, Users.id == Employees.user_id)
                .where(Users.company_id == company_id)
            ).scalars()
        else:
            employee = db.session.query(Employees).filter(Employees.user_id == user.id).first()
            if not employee:
                response_body['message'] = 'Empleado no encontrado'
                response_body['result'] = {}
                return response_body, 404
            rows = db.session.execute(db.select(Applications).where(Applications.employee_id == employee.id)).scalars()
        if not rows:
            response_body['message'] = 'No hay aplicaciones disponibles'
            response_body['result'] = {}
            return response_body, 404
        result = [row.serialize() for row in rows]
        response_body['message'] = 'Listado de todas las solicitudes (GET)'
        response_body['results'] = result
        return response_body, 200
    if request.method == 'POST':
        data = request.json   
        if user.is_app_admin or user.is_company_admin:
            employee = db.session.query(Employees).filter(Employees.user_id == user.id).first()
            is_approved = user.is_company_admin
        else:
            employee = db.session.query(Employees).filter(Employees.user_id == user.id).first()
            is_approved = False
        if not employee:
            response_body['message'] = 'Empleado no encontrado para este usuario.'
            return response_body, 404
        row = Applications(description=data.get('description'),
                           amount=float(data.get('amount')),
                           creation_date=datetime.now(),
                           employee_id=employee.id,
                           is_approved=is_approved)
        db.session.add(row)
        db.session.commit()
        response_body['message'] = 'Solicitud creada exitosamente (POST)'
        response_body['results'] = row.serialize()
        return response_body, 201


@api.route('/histories', methods=['GET', 'POST'])
@jwt_required()
def histories():
    response_body = {}
    current_user = get_jwt_identity()
    user = db.session.get(Users, current_user)
    if not user.is_app_admin and not user.is_company_admin:
        response_body['message'] = 'Permiso denegado'
        return response_body, 403
    if request.method == 'GET':
        rows = db.session.execute(db.select(Histories)).scalars()
        if not rows:
            response_body['message'] = f'Historial no existe'
            response_body['result'] = {}
            return response_body, 404
        result = [row.serialize() for row in rows]
        response_body['message'] = 'Historial encontrado (GET)'
        response_body['results'] = result
        return response_body, 200
    if request.method == 'POST':
        if not user.is_company_admin and not user.is_app_admin and not user.is_employee:
            response_body['message'] = 'Permiso denegado'
            return response_body, 403
        data = request.json
        row = History(period = data.get('period'),
                      amount = data.get('amount'),
                      employee_id=current_user,
                      company_id=user.company_id)
        db.session.add(row)
        db.session.commit()
        response_body['message'] = 'Historial creado exitosamente (POST)'
        response_body['results'] = row.serialize()
        return response_body, 201


@api.route('/expenses', methods=['GET', 'POST'])
@jwt_required()
def expenses():
    response_body = {}
    current_user = get_jwt_identity()
    user = db.session.get(Users, current_user['user_id'])
    if not (user.is_app_admin or user.is_company_admin or user.company_id):
        response_body['message'] = 'Permiso denegado'
        return response_body, 403
    if request.method == 'GET':
        if user.is_app_admin: 
            rows = db.session.query(Expenses).all()
        elif user.is_company_admin:
            rows = db.session.query(Expenses).join(Users).filter(Users.company_id == user.company_id).all()
        else: 
            rows = db.session.query(Expenses).filter(Expenses.user_id == user.id).all()
        if not rows:
            response_body['message'] = 'No hay gastos disponibles'
            response_body['results'] = []
            return response_body, 404
        response_body['message'] = 'Listado de gastos disponibles'
        response_body['results'] = [row.serialize() for row in rows]
        return response_body, 200
    if request.method == 'POST':
        data = request.json
        if not (user.is_app_admin or user.is_company_admin): 
            employee = db.session.query(Employees).filter(Employees.user_id == user.id).first()
            if not employee:
                response_body['message'] = 'Empleado no encontrado'
                return response_body, 404
        new_expense = Expenses(description=data.get('description'),
                               amount=float(data.get('amount', 0)),
                               vouchers=data.get('vouchers'),
                               date=datetime.now(),
                               user_id=user.id)
        db.session.add(new_expense)
        db.session.commit()
        response_body['message'] = 'Gasto creado exitosamente'
        response_body['results'] = new_expense.serialize()
        return response_body, 201


@api.route('/companies/<int:id>', methods=['GET','PUT', 'DELETE'])
@jwt_required()
def company(id):
    response_body = {}
    current_user = get_jwt_identity()
    user = db.session.get(Users, current_user)
    if not user.is_app_admin:
        response_body['message'] = 'Permiso denegado'
        return response_body, 403
    rows = db.session.execute(db.select(Companies).where(Companies.id == id)).scalar()
    if not rows:
        response_body['message'] = f'Compañia no existe'
        response_body['result'] = {}
        return response_body, 404
    if request.method == 'GET':
        response_body['message'] = 'Compañia (GET)'
        response_body['results'] = rows.serialize()
        return response_body, 200
    if request.method == 'PUT':
        data = request.json
        rows.name = data.get('name')
        db.session.commit()
        response_body['message'] = f'La compañía ha sido modificada'
        response_body['result'] = rows.serialize()
        return response_body, 200
    if request.method == 'DELETE':
        db.session.delete(rows)
        db.session.commit()
        response_body['message'] = f'Compañía eliminada existosamente'
        response_body['result'] = {}
        return response_body, 200


@api.route('/administrators/<int:id>', methods=['GET', 'PUT', 'DELETE'])
@jwt_required()
def admin(id):
    response_body = {}
    current_user = get_jwt_identity()
    user = db.session.get(Users, current_user)   
    if not user.is_app_admin and not user.is_company_admin:
        response_body['message'] = 'Permiso denegado'
        return response_body, 403
    rows = db.session.execute(db.select(Administrators).where(Administrators.id == id)).scalar()
    if not rows:
        response_body['message'] = 'Administrador no existe'
        response_body['result'] = {}
        return response_body, 404
    if request.method == 'GET':
        if user.company_id == 0:
            response_body['message'] = 'Administrador encontrado (GET)'
            response_body['results'] = rows.serialize()
            return response_body, 200
        elif rows.company_id != user.company_id:
            response_body['message'] = 'No se encontró el administrador en su compañía'
            response_body['results'] = []
            return response_body, 404
        response_body['message'] = 'Administrador encontrado (GET)'
        response_body['results'] = rows.serialize()
        return response_body, 200
    if request.method == 'PUT':
        data = request.json
        rows.name = data.get('name')
        rows.last_name = data.get('last_name')
        db.session.commit()
        response_body['message'] = f'El Administrador {id} ha sido modificado'
        response_body['result'] = rows.serialize()
        return response_body, 201
    if request.method == 'DELETE':
        db.session.delete(rows)
        db.session.commit()
        response_body['message'] = 'Administrador eliminado'
        response_body['result'] = {}
        return response_body, 200


@api.route('/employees/<int:id>', methods=['GET', 'PUT', 'DELETE'])
@jwt_required()
def employee(id):
    response_body = {}
    current_user = get_jwt_identity()
    user = db.session.get(Users, current_user)
    if not user.is_app_admin and not user.is_company_admin:
        response_body['message'] = 'Permiso denegado'
        return response_body, 403
    rows = db.session.execute(db.select(Employees).where(Employees.id == id)).scalar()
    if not rows:
        response_body['message'] = 'Empleado no existe'
        response_body['result'] = {}
        return response_body, 404
    if request.method == 'GET':
        if user.company_id == 0:
            response_body['message'] = 'Empleado encontrado (GET)'
            response_body['results'] = rows.serialize()
            return response_body, 200
        elif rows.company_id != user.company_id:
            response_body['message'] = 'No se encontró al empleado en su compañía'
            response_body['results'] = []
            return response_body, 404
        response_body['message'] = 'Empleado encontrado (GET)'
        response_body['results'] = rows.serialize()
        return response_body, 200
    if request.method == 'PUT':
        data = request.json
        rows.name = data.get('name')
        rows.last_name = data.get('last_name')
        rows.budget_limit = data.get('budget_limit')
        db.session.commit()
        response_body['message'] = f'El empleado {id} ha sido modificado'
        response_body['result'] = rows.serialize()
        return response_body, 201
    if request.method == 'DELETE':
        db.session.delete(rows)
        db.session.commit()
        response_body['message'] = 'Empleado eliminado'
        response_body['result'] = {}
        return response_body, 200
    

@api.route('/applications/<int:id>', methods=['GET', 'PUT', 'DELETE'])
@jwt_required()
def application(id):
    response_body = {}
    current_user = get_jwt_identity()
    user = db.session.get(Users, current_user['user_id'])
    rows = db.session.execute(db.select(Applications).where(Applications.id == id)).scalar()
    if not rows:
        response_body['message'] = 'Solicitud no existe'
        response_body['result'] = {}
        return response_body, 404
    if not (user.is_app_admin or user.is_company_admin or rows.employee_id == user.id):
        response_body['message'] = 'Permiso denegado'
        return response_body, 403
    if request.method == 'GET':
        response_body['message'] = 'Solicitud encontrada (GET)'
        response_body['results'] = rows.serialize()
        return response_body, 200
    if request.method == 'PUT':
        application = db.session.query(Applications).filter_by(id=id).first()
        if not application:
            response_body['message'] = 'Aplicación no encontrada.'
            return response_body, 404
        employee = db.session.query(Employees).filter_by(user_id=user.id).first()
        if not (user.is_app_admin or user.is_company_admin):
            response_body['message'] = 'El usuario no tiene permisos para aprobar esta solicitud.'
            return response_body, 403
        if not employee:
            response_body['message'] = 'El usuario no está asociado a un empleado válido.'
            return response_body, 400
        application.is_approved = True
        application.approved_date = datetime.now()
        application.approved_by = user.id 
        db.session.commit()
        response_body['message'] = 'Aplicación aprobada exitosamente'
        response_body['result'] = application.serialize() 
        return response_body, 200
    if request.method == 'DELETE':
        db.session.delete(rows)
        db.session.commit()
        response_body['message'] = 'Solicitud eliminada'
        response_body['result'] = {}
        return response_body, 200
    

@api.route('/histories/<int:id>', methods=['GET'])
@jwt_required()
def history(id):
    response_body = {}
    current_user = get_jwt_identity()
    user = db.session.get(Users, current_user)
    if not (user.is_app_admin or user.is_company_admin or user.is_employee):
        response_body['message'] = 'Permiso denegado'
        return response_body, 403
    rows = db.session.execute(db.select(Histories).where(Histories.id == id)).scalar()
    if not rows:
        response_body['message'] = 'Historial no existe'
        response_body['results'] = {}
        return response_body, 404
    if user.is_employee and rows.employee_id != user.id:
        response_body['message'] = 'Permiso denegado para este historial'
        response_body['results'] = {}
        return response_body, 403
    if request.method == 'GET':
        response_body['message'] = 'Historial encontrado (GET)'
        response_body['results'] = rows.serialize()
        return response_body, 200


@api.route('/expenses/<int:id>', methods=['GET', 'PUT', 'DELETE'])
@jwt_required()
def expenditure(id):
    response_body = {}
    current_user = get_jwt_identity()
    user = db.session.get(Users, current_user['user_id'])
    if not (user.is_app_admin or user.is_company_admin or user.is_employee):
        response_body['message'] = 'Permiso denegado'
        return response_body, 403
    rows = db.session.execute(db.select(Expenses).where(Expenses.id == id)).scalar()
    if not rows:
        response_body['message'] = 'Gasto no existe'
        response_body['result'] = {}
        return response_body, 404
    if not (user.is_app_admin or user.is_company_admin or rows.user_id == user.id):
        response_body['message'] = 'Permiso denegado'
        return response_body, 403
    if request.method == 'GET':
        response_body['message'] = 'Gasto encontrado (GET)'
        response_body['results'] = rows.serialize()
        return response_body, 200
    if request.method == 'PUT':
        data = request.json
        rows.amount = data.get('amount')
        rows.vouchers = data.get('vouchers')
        db.session.commit()
        response_body['message'] = f'Gasto {id} ha sido modificado'
        response_body['results'] = rows.serialize()
        return response_body, 200
    if request.method == 'DELETE':
        db.session.delete(rows)
        db.session.commit()
        response_body['message'] = 'Gasto eliminado'
        response_body['results'] = {}
        return response_body, 200


@api.route('/register-company', methods=['POST'])
@jwt_required()
def new_company():
    response_body = {}
    current_user = get_jwt_identity()
    user = db.session.get(Users, current_user['user_id'])
    if not (user.is_app_admin):
        response_body['message'] = 'Permiso denegado'
        return response_body, 403
    data = request.json
    print(data)
    row = Companies(name=data.get('name'),
                    date_recored=datetime.now())
    db.session.add(row)
    db.session.commit()
    user = Users(email=data.get('email'),
                 password=data.get('password'),
                 is_active=True,
                 is_app_admin=False,
                 is_company_admin=True,
                 company_id=row.serialize()['id'])
    db.session.add(user)
    db.session.commit() 
    response_body['message'] = 'Compañía registrada exitosamente'
    response_body['results'] = user.serialize()
    response_body['results']['company'] = row.name
    response_body['results']['company_id'] = row.id
    return response_body, 201


@api.route('/create-applications', methods=['POST'])
@jwt_required()
def new_application():
    response_body = {}
    current_user = get_jwt_identity()
    user = db.session.get(Users, current_user)
    if not (user.is_company_admin or user.is_employee):
        response_body['message'] = 'Permiso denegado para crear una solicitud'
        return response_body, 403
    data = request.json
    row = Applications(description=data.get('description'),
                       amount=data.get('amount'),
                       employee_id=user.id,
                       company_id=user.company_id)
    db.session.add(row)
    db.session.commit()
    response_body['message'] = 'Solicitud registrada exitosamente'
    response_body['results'] = row.serialize()
    return response_body, 201


@api.route('/add-expenses', methods=['POST'])
@jwt_required()
def newExpenditure():
    response_body = {}
    current_user = get_jwt_identity()
    user = db.session.get(Users, current_user)
    if not (user.is_company_admin or user.is_employee):
            user = db.session.get(Users, current_user['user_id'])
            employee = db.session.get(Employees,current_user['user_id'])
    if not (user.is_company_admin or employee or user.is_app_admin):
            response_body['message'] = 'Permiso denegado para crear un gasto'
            return response_body, 403
    data = request.json
    row = Expenses(amount=float(data.get('amount')),
                   vouchers=data.get('vouchers'),
                   date=data.get('date'),
                   description=data.get('description'),
                   user_id=user.id)
    db.session.add(row)
    db.session.commit()
    response_body['message'] = 'Gasto registrado exitosamente'
    response_body['results'] = row.serialize()
    return response_body, 201

