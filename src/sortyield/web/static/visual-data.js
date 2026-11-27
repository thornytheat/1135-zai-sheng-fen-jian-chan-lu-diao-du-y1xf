function drawProjectChart(target, points) {
    const capacity = named('div',undefined,'bunker-capacity');
    const ceiling = Math.max(1,...points.map(item=>Math.abs(item.value)));
    for(const stock of points) {
        const bin=named('section',undefined,'bunker-meter');
        const scale = named('progress');
        scale.max=ceiling; scale.value=Math.abs(stock.value);
        scale.setAttribute('aria-label',stock.label);
        bin.append(named('h3',stock.label),scale,named('b',stock.value));
        capacity.append(bin);
    }
    target.append(capacity);
}
