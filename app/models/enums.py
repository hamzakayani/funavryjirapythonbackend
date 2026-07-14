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


class IssueStatus(str, enum.Enum):
    ToDo = "To Do"
    InProgress = "In Progress"
    InReview = "In Review"
    Done = "Done"
