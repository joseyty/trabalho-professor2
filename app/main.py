from datetime import datetime, timedelta, timezone
from fastapi import FastAPI, Depends, Header, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from .database import Base, engine, SessionLocal
from .models import User, Transfer
from .schemas import RegisterRequest, LoginRequest, TransferRequest
from .security import hash_password, verify_password, create_token, decode_token

app = FastAPI(
    title="API de Transferências",
    description="Carteira digital com autenticação, atomicidade e proteção contra duplicidade.",
    version="1.0.0",
)

@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def reject(status: int, code: str):
    raise HTTPException(status_code=status, detail=code)

@app.exception_handler(HTTPException)
async def http_error_handler(request, exc):
    code = exc.detail if isinstance(exc.detail, str) else "ERRO_REQUISICAO"
    return JSONResponse(status_code=exc.status_code, content={"error": code})

@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    if request.url.path == "/transferencias":
        errors = exc.errors()
        if any("valor" in error.get("loc", ()) for error in errors):
            return JSONResponse(status_code=422, content={"error": "VALOR_INVALIDO"})
    return JSONResponse(status_code=422, content={"error": "DADOS_INVALIDOS"})

@app.exception_handler(IntegrityError)
async def integrity_error_handler(request, exc):
    return JSONResponse(status_code=409, content={"error": "CONFLITO_DADOS"})

def current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    if not authorization or not authorization.startswith("Bearer "):
        reject(401, "NAO_AUTENTICADO")
    token = authorization[7:].strip()
    username = decode_token(token)
    if not username:
        reject(401, "NAO_AUTENTICADO")
    user = db.scalar(select(User).where(User.username == username))
    if not user:
        reject(401, "NAO_AUTENTICADO")
    return user

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/auth/registrar", status_code=201)
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.scalar(select(User).where(User.username == data.username))
    if existing:
        reject(409, "USUARIO_EXISTENTE")
    user = User(username=data.username, password_hash=hash_password(data.password), balance=1000)
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        reject(409, "USUARIO_EXISTENTE")
    return {"username": user.username}

@app.post("/auth/login")
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.username == data.username))
    if not user or not verify_password(data.password, user.password_hash):
        reject(401, "CREDENCIAIS_INVALIDAS")
    return {"token": create_token(user.username)}

@app.get("/conta")
def account(user: User = Depends(current_user), db: Session = Depends(get_db)):
    # Consulta sempre a conta vinculada ao token; não aceita username pelo cliente.
    fresh_user = db.get(User, user.id)
    return {"username": fresh_user.username, "saldo": fresh_user.balance}

@app.post("/transferencias", status_code=201)
def transfer(
    data: TransferRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    if data.destino == user.username:
        reject(422, "MESMA_CONTA")

    # current_user já consultou o banco nesta sessão. Encerramos essa leitura
    # antes de abrir a transação explícita da transferência.
    origin_id = user.id
    db.rollback()

    try:
        # Descobrimos o destino e depois bloqueamos ambas as contas em ordem
        # crescente de ID para reduzir deadlocks em transferências cruzadas.
        destination_id = db.scalar(select(User.id).where(User.username == data.destino))
        if destination_id is None:
            reject(404, "DESTINO_INEXISTENTE")
        db.rollback()  # encerra a consulta usada para localizar o destino

        with db.begin():
            locked_users = db.scalars(
                select(User)
                .where(User.id.in_(sorted([origin_id, destination_id])))
                .order_by(User.id)
                .with_for_update()
            ).all()
            accounts = {account.id: account for account in locked_users}
            origin = accounts[origin_id]
            destination = accounts[destination_id]

            now = datetime.now(timezone.utc)
            cutoff = now - timedelta(seconds=60)
            duplicate = db.scalar(
                select(Transfer.id).where(
                    Transfer.origin_id == origin.id,
                    Transfer.destination_id == destination.id,
                    Transfer.value == data.valor,
                    Transfer.created_at > cutoff,
                ).limit(1)
            )
            # A duplicidade é verificada antes do saldo, conforme o enunciado.
            if duplicate:
                reject(409, "TRANSFERENCIA_DUPLICADA")
            if origin.balance < data.valor:
                reject(409, "SALDO_INSUFICIENTE")

            origin.balance -= data.valor
            destination.balance += data.valor
            record = Transfer(
                origin_id=origin.id,
                destination_id=destination.id,
                value=data.valor,
                created_at=now,
            )
            db.add(record)
            db.flush()
            response = {
                "id": record.id,
                "origem": origin.username,
                "destino": destination.username,
                "valor": data.valor,
                "saldo": origin.balance,
            }
        return response
    except HTTPException:
        db.rollback()
        raise

@app.get("/auditoria")
def audit(db: Session = Depends(get_db)):
    users_count = db.scalar(select(func.count(User.id))) or 0
    balances_sum = db.scalar(select(func.coalesce(func.sum(User.balance), 0))) or 0
    transfers_count = db.scalar(select(func.count(Transfer.id)) ) or 0
    return {
        "usuarios": users_count,
        "somaSaldos": balances_sum,
        "transferencias": transfers_count,
    }
