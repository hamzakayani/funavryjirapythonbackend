import enum


class UserStatus(str, enum.Enum):
    Pending = "Pending"
    Active = "Active"
    Rejected = "Rejected"
    Suspended = "Suspended"


class ProjectRole(str, enum.Enum):
    Lead = "Lead"
    Member = "Member"


# Job-function role a project Lead assigns to a member (distinct from ProjectRole,
# which only governs Lead/Member authority). Free-form list so new IT roles can be
# added without a schema migration — stored as a plain string column.
MEMBER_JOB_ROLES = [
    "QA",
    "Frontend",
    "Backend",
    "AI Engineer",
    "Project Manager",
    "DevOps",
    "QA Automation",
    "Scrum Master",
    "Tech Lead",
    "Other",
]


class SprintStatus(str, enum.Enum):
    Planned = "Planned"
    Active = "Active"
    Completed = "Completed"


class IssueType(str, enum.Enum):
    Epic = "Epic"
    Story = "Story"
    Task = "Task"
    Bug = "Bug"
    SubTask = "Sub-task"


class Priority(str, enum.Enum):
    Highest = "Highest"
    High = "High"
    Medium = "Medium"
    Low = "Low"
    Lowest = "Lowest"


# Default statuses seeded for every project's IssueStatusDef list.
# Issue.status is a free-form string referencing IssueStatusDef.name — no
# longer a fixed enum, since projects can define their own custom statuses.
DEFAULT_STATUSES = ["To Do", "In Progress", "In Review", "Done"]
