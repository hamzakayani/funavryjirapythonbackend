import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.testclient import TestClient

from app.core.security import create_access_token
from app.database import Base, get_db
from app.models import Project, ProjectMember, ProjectRole, User, UserStatus

# IMPORTANT: import main.app but never enter it as `with TestClient(app) as c:`.
# Starlette only runs FastAPI's startup/shutdown lifespan (which seeds demo
# data and starts APScheduler against the REAL settings.database_url) inside
# that `with` block. Plain instantiation below skips lifespan entirely, which
# is what we want for isolated unit/integration tests.
from main import app

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture()
def db_session():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def make_user(
    db,
    *,
    name: str = "User",
    email: str | None = None,
    is_super_admin: bool = False,
    status: UserStatus = UserStatus.Active,
) -> User:
    email = email or f"{name.lower().replace(' ', '')}@example.com"
    user = User(
        name=name,
        email=email,
        password_hash="not-a-real-hash",
        status=status,
        is_super_admin=is_super_admin,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def make_project(db, *, key: str = "PRJ", name: str = "Project", created_by: int | None = None) -> Project:
    if created_by is None:
        created_by = make_user(db, name=f"{key} Creator").id
    project = Project(key=key, name=name, created_by=created_by)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def add_member(db, project: Project, user: User, role: ProjectRole = ProjectRole.Member) -> ProjectMember:
    member = ProjectMember(project_id=project.id, user_id=user.id, project_role=role)
    db.add(member)
    db.commit()
    db.refresh(member)
    return member


def auth_headers(user: User) -> dict:
    token = create_access_token(user.id)
    return {"Authorization": f"Bearer {token}"}
