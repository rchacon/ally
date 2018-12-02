CREATE TABLE ally_transactions(
    id serial primary key,
    posted_at timestamp with time zone NOT NULL,
    type VARCHAR(20) NOT NULL,
    description VARCHAR(100) NOT NULL,
    amount MONEY NOT NULL,
    balance MONEY NOT NULL,
    created_at timestamp with time zone DEFAULT NOW()
);
