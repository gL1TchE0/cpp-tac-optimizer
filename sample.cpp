#include <iostream>
using namespace std;

int add(int x,int y)
{
    return x + y;
}

int main()
{
    int a = 5;
    int b = 10;

    int c = a + b;
    int d = a + b;        // CSE

    int e = 5 * 4;        // constant folding

    int f = e;            // copy propagation

    int g = c * 2;        // strength reduction

    int h = g + 0;        // algebraic simplification

    int dead = a * b;     // dead code

    if(0)
    {
        cout<<"never executes";  // unreachable
    }

    int sum = add(a,b);   // function optimization

    for(int i=0;i<5;i++)
    {
        int t = i * 2;    // loop optimization
    }

    cout<<sum<<endl;

    return 0;
}