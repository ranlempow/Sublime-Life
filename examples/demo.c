#include <stdio.h>
#define QuantumToCharToQuantumEqQuantum(quantum) \
  ((ScaleCharToQuantum((unsigned char) ScaleQuantumToChar(quantum))) == quantum)
    MagickBooleanType
      ok_to_reduce=MagickFalse;

#define PNG_WRITE_EMPTY_PLTE_SUPPORTED 1

static int main(int a, float *b)
{
    int n1, n2;
    int stack[100];
    
    printf("Enter two positive integers: ");
    scanf("%d %d",&n1,&n2);

    while(n1!=n2)
    {
        if(n1 > n2)
            n1 -= n2;
        else
            n2 -= n1;
    }
#ifdef PNG_WRITE_EMPTY_PLTE_SUPPORTED
    printf("GCD = %d",n1);
#endif
    return 0;
}