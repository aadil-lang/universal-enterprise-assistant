/**
 * Archie Personalized Greeting Service (ESR-STD-v2.4 §5).
 * 
 * Rules:
 * - Greet the currently authenticated employee using preferred name.
 * - Fallback order: preferred_name -> first_name -> display name -> neutral greeting.
 * - Local time greeting: Morning (< 12), Afternoon (12 to 17), Evening (>= 17).
 * - Greet once when a voice session begins; do not repeat greeting after every utterance.
 * - Never trust a user-spoken name as identity proof.
 */

import type { ArchieUserProfile } from './types.ts';

export class GreetingService {
  private hasGreetedSession: boolean = false;

  /**
   * Generates time-of-day appropriate greeting for the authenticated employee.
   */
  public generateGreeting(user?: ArchieUserProfile | null, now: Date = new Date()): string {
    const hours = now.getHours();
    let timeGreeting = 'Good afternoon';
    if (hours < 12) {
      timeGreeting = 'Good morning';
    } else if (hours >= 17) {
      timeGreeting = 'Good evening';
    }

    const name = this.resolveEmployeeName(user);

    if (name) {
      return (
        `Hey ${name}! ${timeGreeting}. I am Archie, your universal Enterprise HR and IT Assistant here at Acme Corporation. ` +
        `I am fully equipped to assist you with everything related to our workplace policies, your personal employment records, and IT support services. ` +
        `You can ask me about company guidelines including annual leave accruals, sick leave rollover caps, remote work and VPN policies, ergonomic home-office allowances, wellness benefits, and hardware refresh cycles. ` +
        `I can also look up your live verified leave balances, inspect your assigned laptop and hardware assets, check the status of your open support tickets, or help draft requests for time off, expense reimbursements, and equipment support. ` +
        `How can I assist you today?`
      );
    }

    // Neutral fallback
    return (
      `Hello! ${timeGreeting}. I am Archie, your universal Enterprise HR and IT Assistant here at Acme Corporation. ` +
      `I am here to help you navigate all company policies, access your personal employment records, and assist with workplace requests. ` +
      `You can ask me about company guidelines including leave rules, remote work security, and equipment stipends, check your personal leave balances and assigned hardware, or submit service requests. ` +
      `How can I help you today?`
    );
  }

  public shouldGreet(): boolean {
    return !this.hasGreetedSession;
  }

  public markGreeted(): void {
    this.hasGreetedSession = true;
  }

  public resetSession(): void {
    this.hasGreetedSession = false;
  }

  private resolveEmployeeName(user?: ArchieUserProfile | null): string | null {
    if (!user) return null;

    if (user.preferred_name && user.preferred_name.trim().length > 0) {
      return user.preferred_name.trim();
    }

    if (user.first_name && user.first_name.trim().length > 0) {
      return user.first_name.trim();
    }

    if (user.last_name && user.last_name.trim().length > 0) {
      return user.last_name.trim();
    }

    return null;
  }
}
