Migration plan: moving from first_name/last_name to full_name

Goal
- Safely migrate existing database and user data from separate first_name & last_name fields to a single full_name field on CustomUser, without data loss.

High-level strategy
1. Add new field full_name (nullable) while keeping first_name and last_name intact.
2. Backfill full_name from existing first_name and last_name for all users.
3. Update code to read/write full_name (done in code changes). Keep first_name/last_name in models until backfill + verification.
4. Create a migration to remove first_name and last_name (optional) after the codebase and migrations across environments are updated.

Detailed steps
- Development branch (local)
  1. Ensure current codebase is committed.
  2. Add a new migration that:
     - Adds `full_name = models.CharField(max_length=120, null=True)` to `CustomUser`.
     - Leaves `first_name` and `last_name` as-is.
  3. Run `python manage.py makemigrations accounts` and `python manage.py migrate` locally.
  4. Backfill data: write a Django data migration or a small management command that sets `full_name = f"{first_name} {last_name}"` where full_name is empty/null, handling edge cases (missing parts).
     Example management command pseudo:
       for user in CustomUser.objects.filter(full_name__isnull=True):
           parts = filter(None, [user.first_name, user.last_name])
           user.full_name = " ".join(parts) or user.email.split('@')[0]
           user.save()
  5. Run the test suite and any manual sanity checks.

- Staging/production rollout
  Option A (safer, preferred):
    1. Deploy code that includes the new `full_name` field and code paths that prefer `full_name` but still fall back to `first_name/last_name` if needed.
    2. Run the backfill migration/management command on production to populate `full_name`.
    3. Monitor logs and perform smoke tests.
    4. Once verified, deploy the code that removes `first_name` and `last_name` (this requires a migration to drop those columns). Run migrations.

  Option B (one-shot - riskier):
    1. Make the model change to remove `first_name`/`last_name` and add `full_name` + data migration in a single migration. This may risk downtime if migrations fail. Not recommended for production with live data.

Edge cases & notes
- Users who only had first_name or only last_name: join the non-empty part as full_name.
- Users with international names: preserve the exact concatenation; if preferred, you can add logic to prefer last_name first.
- Email-based fallback: if both name fields are empty, set full_name to the local part of the email address to avoid nulls.
- Data retention: keep previous name fields for at least a few releases (as backups) before dropping them.
- Backups: always take a DB backup before running migrations on production.

Testing
- Run migration and backfill on a DB snapshot of production in a staging environment.
- Run the full test suite.
- Sample SQL to verify:
  SELECT id, first_name, last_name, full_name FROM accounts_customuser WHERE full_name IS NULL OR full_name = '';

Rollout timeline suggestion
- Day 0: deploy code with new field & backfill migration (no destructive change). Run backfill.
- Day 1-3: monitor logs and app behavior.
- Day 4: deploy code that removes old fields and run destructive migration.

If you want, I can:
- Generate the exact Django migration files (add field + data migration, then a drop-field migration) for this repository.
- Create a management command to perform the backfill with safer logging and batching.
- Provide a rollback plan and test harness.

Contact me which variant you prefer (I can create the migrations + management command now).