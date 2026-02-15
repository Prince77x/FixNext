##  relationship of schema
Tenant → Tickets
Property → Units
Unit → Tickets
Ticket → Assignments
Ticket → History
Ticket → Attachments
Technician → Assignments


## manager dashboard
📊 Tenant Stats (Top Cards)
├── Total Active Tenants     [Count]
├── Vacant Units            [Count]  
├── Tickets per Tenant      [Avg]
└── New Tenants This Month  [Count]

👥 Tenant List (Filterable Table)
├── Filter: Status | Unit | Property | Move-in Date
├── Columns: Name | Email | Unit | Property | Status | Move-in | Actions
└── Bulk Actions: Send Notice | Mark Inactive | Export

➕ Quick Actions
├── Add New Tenant
├── Import CSV
├── Send Bulk Email
└── Generate Reports


## workers dashboard
📊 My Stats (Top Cards)
├── Assigned Tickets: 12    [TicketAssignment count]
├── In Progress: 3         [Ticket.status = IN_PROGRESS]
├── Completed Today: 5     [Ticket.status = DONE]
└── Avg Completion Time    [calculated]

🎯 My Assigned Tickets (Filterable Table)
├── Filters: Status | Priority | Property | Date Range
├── Columns: ID | Title | Unit | Priority | Status | Assigned Date | Actions
└── Bulk: Mark Complete | Update Status

⚙️ Quick Actions
├── Accept/Reject Assignment
├── Update Status (In Progress/Done)
├── Add Notes/History
├── Upload Photos (Attachment)
└── View Ticket History

📋 My Schedule (Timeline)
├── Today | This Week | Upcoming
└── Assigned vs Completed
