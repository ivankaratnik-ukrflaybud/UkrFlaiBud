# Production Order Architecture

Sprint 7 adds `backend/app/modules/production` using the same Clean Architecture layout as Inventory and BOM:

- `domain`: workflow enums;
- `infrastructure`: SQLAlchemy models and repositories;
- `application/services`: separate services for orders, requirements, reservations, material issue/return, consumption, completion, serials, documents and queries;
- `presentation/routes`: split FastAPI routes under `/api/v1/production`.

## BOM Snapshot

Production orders reference an approved BOM version and store an immutable `production_order_bom_snapshots` row. Material requirements are copied from BOM lines into `production_material_requirements`, preserving display names, units, source type, optional/alternative flags and waste percentage.

Later BOM, item or unit renames do not alter existing production-order documents.

## Reservation Model

Reservations are stored in `production_material_reservations`. They are warehouse-specific and reduce available quantity for other production orders, but they do not create Inventory movements. Physical stock remains sourced from `inventory_stock_balances`.

Availability is calculated as:

`physical stock - active reservations for other production orders`

## Inventory Integration

Material issue and return use the existing Inventory `DocumentService`:

- issue posts an `issue` inventory document from the material warehouse;
- return posts a `return_in` inventory document back to the material warehouse;
- completion posts a `receipt` inventory document into the finished-goods warehouse.

Production stores business-level transaction links in `production_material_transactions` and `production_material_transaction_lines`.

## Consumption and Scrap

Consumption and scrap are production accounting controls over issued material. They validate that consumed + scrapped + returned quantity does not exceed issued quantity. They do not mutate immutable Inventory movements.

## Status Transitions

Orders follow the configured workflow from draft to planned, released, reserved, in progress, partial/final completion, suspension or cancellation. Invalid transitions raise conflict errors. Completed and cancelled orders are read-only.

## Permissions and Scope

The module seeds `production.*` permissions and a `production_manager` role. Routes require permission-based access and pass the current user into services so site and warehouse scope is enforced through Inventory scope helpers.

## Deferred Scope

Purchasing, supplier management, accounting valuation, payroll, detailed CNC scheduling, transport-box-specific workflow, QC laboratory flows, equipment maintenance and full MRP planning are intentionally not implemented in Sprint 7.
