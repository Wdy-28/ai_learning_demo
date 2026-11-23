#include<stdio.h>
# define PI 3.14159
int main(){
	double r,s;
	printf("请输入圆的半径=");
	scanf("%lf",&r);
	s=PI*r*r;
	printf("圆的面积=");
	printf("%0.4lf",s);
	return 0;
}          
