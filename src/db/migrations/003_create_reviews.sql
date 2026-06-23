create table if not exists reviews (
    id bigint generated always as identity primary key,
    app_id integer not null references steam_games(app_id) on delete cascade,
    publisher text not null,
    title text not null,
    subtitle text,
    rating numeric,
    rating_scale numeric,
    source_url text not null unique,
    content jsonb not null check (jsonb_typeof(content) = 'array'),
    fetched_at timestamptz not null default now()
);

create index if not exists reviews_app_id_idx on reviews(app_id);
