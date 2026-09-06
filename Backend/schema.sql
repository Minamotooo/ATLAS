-- ATLAS — live Supabase schema (public)
-- Source of truth, provided verbatim from the Supabase dashboard.
-- Keep this file in sync by hand whenever the DB changes; nothing generates it.
--
-- Notes for anyone writing against these tables:
--   * questions.topic is a FOREIGN KEY to ontology_topics(topic_code) — it stores a
--     topic CODE ("MAT_MATRIX"), never a display label ("Matrices and Determinants").
--   * There is no unique constraint on questions other than the surrogate id, so a
--     naive re-run of any loader will duplicate rows. Dedup before inserting.
--   * question_options.option_label is CHECK-constrained to exactly A/B/C/D.
--   * skills.skill_description is NOT NULL (empty string is acceptable, NULL is not).
--   * There is no subject column anywhere, and no p_transition column on user_skill.

create table public.users (
  user_id uuid not null default gen_random_uuid (),
  user_name text not null,
  created_at timestamp with time zone not null default now(),
  constraint users_pkey primary key (user_id),
  constraint users_user_name_key unique (user_name)
) TABLESPACE pg_default;

create table public.user_skill (
  user_id uuid not null,
  skill_id text not null,
  mastery_level double precision not null default 0.0,
  constraint user_skill_pkey primary key (user_id, skill_id),
  constraint user_skill_skill_id_fkey foreign KEY (skill_id) references skills (skill_id) on delete CASCADE,
  constraint user_skill_user_id_fkey foreign KEY (user_id) references users (user_id) on delete CASCADE
) TABLESPACE pg_default;

create table public.skills (
  skill_id text not null,
  skill_description text not null,
  created_at timestamp with time zone not null default now(),
  constraint skills_pkey primary key (skill_id)
) TABLESPACE pg_default;

create table public.questions (
  id bigserial not null,
  skill_id text not null,
  bloom_level text not null,
  topic text not null,
  question_stem text not null,
  created_at timestamp with time zone not null default now(),
  constraint questions_pkey primary key (id),
  constraint questions_skill_id_fkey foreign KEY (skill_id) references skills (skill_id),
  constraint questions_topic_fkey foreign KEY (topic) references ontology_topics (topic_code)
) TABLESPACE pg_default;

create table public.question_options (
  id bigserial not null,
  question_id bigint not null,
  option_label text not null,
  option_text text not null,
  is_correct boolean not null default false,
  explanation text null,
  created_at timestamp with time zone not null default now(),
  constraint question_options_pkey primary key (id),
  constraint question_options_question_id_option_label_key unique (question_id, option_label),
  constraint question_options_question_id_fkey foreign KEY (question_id) references questions (id) on delete CASCADE,
  constraint question_options_option_label_check check (
    (
      option_label = any (array['A'::text, 'B'::text, 'C'::text, 'D'::text])
    )
  )
) TABLESPACE pg_default;

create table public.option_missing_prerequisites (
  option_id bigint not null,
  missing_skill_id text not null,
  constraint option_missing_prerequisites_pkey primary key (option_id, missing_skill_id),
  constraint option_missing_prerequisites_missing_skill_id_fkey foreign KEY (missing_skill_id) references skills (skill_id),
  constraint option_missing_prerequisites_option_id_fkey foreign KEY (option_id) references question_options (id) on delete CASCADE
) TABLESPACE pg_default;

create index IF not exists idx_option_missing_skill_id on public.option_missing_prerequisites using btree (missing_skill_id) TABLESPACE pg_default;

create index IF not exists idx_option_missing_option_id on public.option_missing_prerequisites using btree (option_id) TABLESPACE pg_default;

create table public.ontology_topics (
  topic_code text not null,
  topic_label text not null,
  constraint ontology_topics_pkey primary key (topic_code)
) TABLESPACE pg_default;

create table public.ontology_skill_topics (
  topic_code text not null,
  skill_id text not null,
  constraint ontology_skill_topics_pkey primary key (topic_code, skill_id),
  constraint ontology_skill_topics_skill_id_fkey foreign KEY (skill_id) references skills (skill_id) on delete CASCADE,
  constraint ontology_skill_topics_topic_code_fkey foreign KEY (topic_code) references ontology_topics (topic_code) on delete CASCADE
) TABLESPACE pg_default;

create table public.ontology_skill_edges (
  source_skill_id text not null,
  target_skill_id text not null,
  constraint ontology_skill_edges_pkey primary key (source_skill_id, target_skill_id),
  constraint ontology_skill_edges_source_skill_id_fkey foreign KEY (source_skill_id) references skills (skill_id) on delete CASCADE,
  constraint ontology_skill_edges_target_skill_id_fkey foreign KEY (target_skill_id) references skills (skill_id) on delete CASCADE
) TABLESPACE pg_default;
