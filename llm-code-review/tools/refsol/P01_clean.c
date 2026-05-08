/*
 * P01 reference solution for Phase 2 V4 verification.
 * Hand-written by a human; used as a control sample for the AI-usage assessment.
 *
 * Spec recap (paraphrased):
 *   Read 20 integers, then output min, max, average (2 decimals)
 *   over the values at odd-numbered positions (1st, 3rd, 5th, ... in 1-based).
 */
#include <stdio.h>

int main(void) {
    int x;
    int min = 0, max = 0;
    long sum = 0;
    int count = 0;

    for (int i = 1; i <= 20; i++) {
        if (scanf("%d", &x) != 1) return 1;
        if (i % 2 == 1) {
            if (count == 0) {
                min = max = x;
            } else {
                if (x < min) min = x;
                if (x > max) max = x;
            }
            sum += x;
            count++;
        }
    }

    double avg = (count > 0) ? ((double)sum / count) : 0.0;
    printf("%d %d %.2f\n", min, max, avg);
    return 0;
}
