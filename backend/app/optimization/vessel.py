from app.domain.models import Money, Recommendation, VesselOption


def recommend(options: list[VesselOption]) -> Recommendation:
    eligible = [o for o in options if o.feasibility.status != 'FAIL' and o.voyage.arrival_feasible]
    eligible.sort(key=lambda o: (o.cost.total_logistics_cost, o.feasibility.voyage_count,
                                 o.voyage.estimated_total_days, o.vessel.name))
    if not eligible:
        return Recommendation(recommended_vessel=None, feasible=False, decision='NO_FEASIBLE_OPTION',
            reason_codes=['NO_OPTION_MEETS_PORT_AND_DEADLINE_CONSTRAINTS'], estimated_cost=None,
            human_explanation=['No evaluated vessel meets both port restrictions and the required arrival date. Review detailed checks or revise the shipment.'])
    best = eligible[0]
    reasons = [
        'Passes draft, LOA, beam and cargo-type checks at both demo ports.',
        f'Cargo delivered in {best.feasibility.voyage_count} sequential voyage(s).',
        f'Estimated arrival {best.voyage.estimated_arrival.isoformat()} meets the deadline.',
        'Lowest total USD logistics cost among port-compatible options that meet the deadline; ties use fewer voyages, then shorter duration.',
    ]
    if len(eligible) > 1:
        reasons.append(f'USD {eligible[1].cost.total_logistics_cost-best.cost.total_logistics_cost:,.2f} below next eligible option ({eligible[1].vessel.name}).')
    return Recommendation(recommended_vessel=best.vessel.name, feasible=True, decision='VESSEL_SELECTED',
        reason_codes=['PORT_CHECKS_PASS', 'CAPACITY_ACCOUNTED', 'DEADLINE_MET', 'MINIMUM_ELIGIBLE_COST'],
        human_explanation=reasons, estimated_cost=Money(amount=best.cost.total_logistics_cost))
