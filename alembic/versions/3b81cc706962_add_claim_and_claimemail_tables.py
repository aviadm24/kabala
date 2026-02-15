"""Add Claim and ClaimEmail tables for email loop closure

Revision ID: 3b81cc706962
Revises: 2a70ab595851
Create Date: 2026-02-13 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '3b81cc706962'
down_revision: Union[str, None] = '2a70ab595851'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create Claim and ClaimEmail tables"""
    # Create claims table
    op.create_table(
        'claims',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('public_id', sa.String(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('reply_email', sa.String(), nullable=False),
        sa.Column('outbound_message_id', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=False),  # Using String for Enum
        sa.Column('insurance_company', sa.String(), nullable=True),
        sa.Column('insurance_contact_email', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('last_inbound_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('public_id'),
    )
    
    # Create indexes on claims
    op.create_index('ix_claims_id', 'claims', ['id'])
    op.create_index('ix_claims_public_id', 'claims', ['public_id'])
    op.create_index('ix_claims_user_id', 'claims', ['user_id'])
    op.create_index('ix_claims_reply_email', 'claims', ['reply_email'])
    op.create_index('ix_claims_status', 'claims', ['status'])
    
    # Create claim_emails table
    op.create_table(
        'claim_emails',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('claim_id', sa.Integer(), nullable=False),
        sa.Column('direction', sa.String(), nullable=False),  # OUTBOUND/INBOUND
        sa.Column('message_id', sa.String(), nullable=True),
        sa.Column('sender', sa.String(), nullable=False),
        sa.Column('recipient', sa.String(), nullable=False),
        sa.Column('subject', sa.String(), nullable=True),
        sa.Column('body_text', sa.Text(), nullable=True),
        sa.Column('body_html', sa.Text(), nullable=True),
        sa.Column('attachments_json', sa.Text(), nullable=True),
        sa.Column('raw_headers_json', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['claim_id'], ['claims.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    
    # Create indexes on claim_emails
    op.create_index('ix_claim_emails_id', 'claim_emails', ['id'])
    op.create_index('ix_claim_emails_claim_id', 'claim_emails', ['claim_id'])
    op.create_index('ix_claim_emails_direction', 'claim_emails', ['direction'])
    op.create_index('ix_claim_emails_message_id', 'claim_emails', ['message_id'])
    op.create_index('ix_claim_emails_created_at', 'claim_emails', ['created_at'])


def downgrade() -> None:
    """Remove Claim and ClaimEmail tables"""
    # Drop indexes
    op.drop_index('ix_claim_emails_created_at', 'claim_emails')
    op.drop_index('ix_claim_emails_message_id', 'claim_emails')
    op.drop_index('ix_claim_emails_direction', 'claim_emails')
    op.drop_index('ix_claim_emails_claim_id', 'claim_emails')
    op.drop_index('ix_claim_emails_id', 'claim_emails')
    
    op.drop_index('ix_claims_status', 'claims')
    op.drop_index('ix_claims_reply_email', 'claims')
    op.drop_index('ix_claims_user_id', 'claims')
    op.drop_index('ix_claims_public_id', 'claims')
    op.drop_index('ix_claims_id', 'claims')
    
    # Drop tables
    op.drop_table('claim_emails')
    op.drop_table('claims')
