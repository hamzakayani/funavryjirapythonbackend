import enum


class UserStatus(str, enum.Enum):
    Pending = "Pending"
    Active = "Active"
    Rejected = "Rejected"
    Suspended = "Suspended"


class ProjectRole(str, enum.Enum):
    Lead = "Lead"
    Member = "Member"


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
