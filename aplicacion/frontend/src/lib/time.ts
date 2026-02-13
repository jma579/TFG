export function minutesFromHHMM(hhmm: string) {
  const [h, m] = hhmm.split(':').map(Number);
  return h * 60 + m;
}

export function hhmmFromMinutes(total: number) {
  const h = Math.floor(total / 60);
  const m = total % 60;
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
}

export function generateTimeSlots(startHHMM: string, endHHMM: string, stepMin = 30) {
  const start = minutesFromHHMM(startHHMM);
  const end = minutesFromHHMM(endHHMM);
  const slots: string[] = [];
  for (let t = start; t < end; t += stepMin) slots.push(hhmmFromMinutes(t));
  return slots;
}

export function overlapsSlot(slotStartHHMM: string, stepMin: number, rangeStartHHMM: string, rangeEndHHMM: string) {
  const slotStart = minutesFromHHMM(slotStartHHMM);
  const slotEnd = slotStart + stepMin;
  const rStart = minutesFromHHMM(rangeStartHHMM);
  const rEnd = minutesFromHHMM(rangeEndHHMM);
  return slotStart < rEnd && slotEnd > rStart;
}
